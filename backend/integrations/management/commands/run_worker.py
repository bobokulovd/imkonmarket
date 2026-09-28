"""Marketplace fon vazifalari worker'i.

    python manage.py run_worker            # doimiy ishlaydi (docker-compose `worker` servisi)
    python manage.py run_worker --once     # navbatdagilarni bajarib chiqadi (test / cron)
"""
import logging
import signal
import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from integrations import jobs
from integrations import services  # noqa: F401  (handlerlarni ro'yxatdan o'tkazadi)
from integrations.redact import redact

log = logging.getLogger("integrations.worker")


class Command(BaseCommand):
    help = "Marketplace integratsiyasi fon vazifalarini bajaradi"

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")
        parser.add_argument("--sleep", type=float, default=2.0)
        parser.add_argument("--schedule-every", type=float, default=30.0)

    def handle(self, *args, **opts):
        self.stop = False
        signal.signal(signal.SIGTERM, self._stop)
        signal.signal(signal.SIGINT, self._stop)
        if opts["once"]:
            jobs.requeue_stale()
            services.schedule_periodic()
            n = jobs.run_pending()
            self.stdout.write(f"bajarildi: {n}")
            return
        log.info("worker ishga tushdi")
        last_schedule = 0.0
        while not self.stop:
            close_old_connections()
            try:
                if time.monotonic() - last_schedule > opts["schedule_every"]:
                    jobs.requeue_stale()
                    services.schedule_periodic()
                    last_schedule = time.monotonic()
                job = jobs.claim()
                if job:
                    jobs.run(job)
                    log.info("job %s %s -> %s %s", job.id, job.kind, job.status, redact(job.last_error)[:200])
                    continue
            except Exception as e:  # noqa: BLE001 — worker to'xtamasligi kerak
                log.error("worker xatosi: %s", redact(repr(e)))
                time.sleep(5)
            time.sleep(opts["sleep"])
        log.info("worker to'xtadi")

    def _stop(self, *a):
        self.stop = True
