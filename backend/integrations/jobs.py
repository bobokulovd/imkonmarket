"""Bazadagi vazifalar navbati.

- HTTP so'rov faqat enqueue() qiladi, tashqi API'ga worker murojaat qiladi (manage.py run_worker).
- Postgres'da SELECT ... FOR UPDATE SKIP LOCKED — bir nechta worker xavfsiz ishlaydi.
- Bitta kabinetning vazifalari ketma-ket bajariladi (marketplace'larning parallel cheklovlari uchun).
- 429/420/5xx/timeout → eksponensial backoff (+jitter, Retry-After hisobga olinadi).
"""
import logging
import random
import traceback
from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .clients.base import AuthError, MarketplaceError, NotSupported, RetryableError
from .models import Job, MarketplaceAccount
from .redact import redact

log = logging.getLogger("integrations.jobs")

HANDLERS = {}
LOCK_SECONDS = 1800
BACKOFF_BASE, BACKOFF_MAX = 2, 300


def handler(kind):
    def deco(fn):
        HANDLERS[kind] = fn
        return fn
    return deco


def enqueue(kind, account=None, payload=None, delay=0, dedupe=None, max_attempts=6) -> Job:
    """dedupe berilsa va shu kalitli navbatdagi vazifa bo'lsa — yangisi yaratilmaydi (payload birlashtiriladi)."""
    run_after = timezone.now() + timedelta(seconds=delay)
    if dedupe:
        existing = Job.objects.filter(dedupe_key=dedupe, status=Job.QUEUED).first()
        if existing:
            old, new = existing.payload or {}, payload or {}
            merged = {**old, **new}
            if isinstance(old.get("ids"), list) and isinstance(new.get("ids"), list):
                merged["ids"] = sorted(set(old["ids"]) | set(new["ids"]))
            else:
                merged.pop("ids", None)  # biri "hammasi" bo'lsa — hammasi
            if old.get("force") or new.get("force"):
                merged["force"] = True
            if merged != old:
                existing.payload = merged
                existing.save(update_fields=["payload"])
            return existing
    return Job.objects.create(kind=kind, account=account, payload=payload or {}, run_after=run_after,
                              dedupe_key=dedupe or "", max_attempts=max_attempts)


def backoff_seconds(attempt: int, retry_after=None) -> float:
    if retry_after:
        return min(float(retry_after), 3600) + random.uniform(0, 1)
    base = min(BACKOFF_BASE ** attempt, BACKOFF_MAX)
    return base + random.uniform(0, base / 2)


def requeue_stale():
    """Worker o'lib qolsa — muddati o'tgan 'running' vazifalarni qaytarish (urinishlar tugagan bo'lsa — failed)."""
    from django.db.models import F
    stale = Job.objects.filter(status=Job.RUNNING, locked_until__lt=timezone.now())
    stale.filter(attempts__gte=F("max_attempts")).update(status=Job.FAILED, last_error="worker timeout",
                                                          finished_at=timezone.now(), locked_until=None)
    stale.update(status=Job.QUEUED, locked_until=None)


def claim() -> Job | None:
    now = timezone.now()
    busy = Job.objects.filter(status=Job.RUNNING, locked_until__gte=now, account__isnull=False).values("account_id")
    with transaction.atomic():
        job = (Job.objects.select_for_update(skip_locked=True)
               .filter(status=Job.QUEUED, run_after__lte=now)
               .filter(Q(account__isnull=True) | ~Q(account_id__in=busy))
               .order_by("run_after", "id").first())
        if not job:
            return None
        job.status = Job.RUNNING
        job.locked_until = now + timedelta(seconds=LOCK_SECONDS)
        job.attempts += 1
        job.save(update_fields=["status", "locked_until", "attempts"])
    # Ikki worker bir vaqtda bitta kabinet vazifasini olgan bo'lsa — keyingisi chekinadi
    if job.account_id and Job.objects.filter(account_id=job.account_id, status=Job.RUNNING,
                                             locked_until__gte=now).exclude(pk=job.pk).exists():
        Job.objects.filter(pk=job.pk).update(status=Job.QUEUED, locked_until=None, attempts=job.attempts - 1,
                                             run_after=now + timedelta(seconds=3))
        return None
    return job


def run(job: Job):
    fn = HANDLERS.get(job.kind)
    if not fn:
        return _finish(job, Job.FAILED, error=f"unknown job kind {job.kind}")
    if job.account_id:
        acc = MarketplaceAccount.objects.filter(pk=job.account_id).first()
        if acc is None or not acc.is_enabled:
            return _finish(job, Job.DONE, result={"skipped": "account disabled"})
        if job.kind != "check_account":
            if acc.status == MarketplaceAccount.ST_INVALID:
                return _finish(job, Job.DONE, result={"skipped": "invalid key"})
            if acc.status == MarketplaceAccount.ST_NEW:  # kalit hali tekshirilmagan — kutamiz
                Job.objects.filter(pk=job.pk).update(status=Job.QUEUED, locked_until=None, attempts=job.attempts - 1,
                                                     run_after=timezone.now() + timedelta(seconds=20))
                return job
        job.account = acc
    try:
        result = fn(job) or {}
    except RetryableError as e:
        if job.attempts < job.max_attempts:
            delay = backoff_seconds(job.attempts, e.retry_after)
            job.status, job.run_after, job.locked_until = Job.QUEUED, timezone.now() + timedelta(seconds=delay), None
            job.last_error = redact(str(e))[:2000]
            job.save(update_fields=["status", "run_after", "locked_until", "last_error"])
            log.info("job %s %s retry in %.0fs: %s", job.id, job.kind, delay, job.last_error)
            return job
        _on_final_failure(job, e)
        return _finish(job, Job.FAILED, error=str(e))
    except AuthError as e:
        _mark_invalid(job.account, e)
        _on_final_failure(job, e)
        return _finish(job, Job.FAILED, error=str(e))
    except (MarketplaceError, NotSupported) as e:
        _on_final_failure(job, e)
        return _finish(job, Job.FAILED, error=str(e))
    except Exception as e:  # noqa: BLE001
        log.error("job %s %s crashed: %s", job.id, job.kind, redact(traceback.format_exc()))
        _on_final_failure(job, e)
        return _finish(job, Job.FAILED, error=f"{type(e).__name__}: {e}")
    return _finish(job, Job.DONE, result=result)


def _finish(job, status, error="", result=None):
    job.status = status
    job.locked_until = None
    job.finished_at = timezone.now()
    job.last_error = redact(error)[:2000]
    if result is not None:
        job.result = result
    job.save(update_fields=["status", "locked_until", "finished_at", "last_error", "result"])
    return job


def _mark_invalid(account, err):
    if not account:
        return
    MarketplaceAccount.objects.filter(pk=account.pk).update(
        status=MarketplaceAccount.ST_INVALID, status_message=redact(str(err))[:500], last_checked_at=timezone.now())


def _on_final_failure(job, err):
    """Vazifa butunlay muvaffaqiyatsiz bo'lsa — tegishli listinglarga xato matnini yozish."""
    from .models import MarketplaceListing
    ids = job.payload.get("ids") if isinstance(job.payload, dict) else None
    if ids and job.kind in ("publish", "poll_status"):
        text = redact(str(err))[:2000]
        MarketplaceListing.objects.filter(pk__in=ids, account=job.account).exclude(
            status=MarketplaceListing.ST_ACTIVE).update(status=MarketplaceListing.ST_ERROR, last_error=text,
                                                        last_synced_at=timezone.now())


def run_pending(limit=100) -> int:
    """Testlar va --once rejimi uchun: navbatdagi (vaqti kelgan) vazifalarni bajaradi."""
    n = 0
    while n < limit:
        job = claim()
        if not job:
            break
        run(job)
        n += 1
    return n
