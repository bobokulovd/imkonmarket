"""Click va Payme integratsiyasi.

Merchant kalitlari (.env) bo'lmasa — DEMO rejim: to'lov sahifasi saytning /pay/demo/<id> sahifasiga
yo'naltiriladi va u yerda "To'lash (Demo)" tugmasi to'lovni tasdiqlaydi. Sayt va ilovada "Demo" belgisi chiqadi.

Payme: Merchant API (JSON-RPC) — POST /api/payments/payme/
Click: SHOP API — POST /api/payments/click/prepare/ va /api/payments/click/complete/
Hisob parametri (account / merchant_trans_id): shartnoma ID si.
"""
import base64
import hashlib
import time
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Contract, Payment
from .services import log, register_payment


def payme_enabled():
    return bool(settings.PAYME_MERCHANT_ID and settings.PAYME_KEY)


def click_enabled():
    return bool(settings.CLICK_SERVICE_ID and settings.CLICK_MERCHANT_ID and settings.CLICK_SECRET_KEY)


def is_demo(method):
    return not (payme_enabled() if method == "payme" else click_enabled() if method == "click" else True)


def checkout_url(contract: Contract, method: str, lang="uz") -> dict:
    amount = contract.due_amount
    if amount <= 0:
        return {"paid": True}
    return_url = f"{settings.SITE_URL.rstrip('/')}/order/{contract.application.token}"
    if is_demo(method):
        p = Payment.objects.create(contract=contract, method=method, amount=amount, is_demo=True)
        return {"demo": True, "url": f"{settings.SITE_URL.rstrip('/')}/pay/demo/{p.id}?c={contract.token}", "payment_id": p.id}
    if method == "payme":
        tiyin = int(amount * 100)
        l = "ru" if lang == "ru" else "en" if lang == "en" else "uz"
        raw = f"m={settings.PAYME_MERCHANT_ID};ac.contract_id={contract.id};a={tiyin};c={return_url};l={l}"
        host = "https://checkout.test.paycom.uz" if settings.PAYME_TEST else "https://checkout.paycom.uz"
        return {"demo": False, "url": f"{host}/{base64.b64encode(raw.encode()).decode()}"}
    if method == "click":
        from urllib.parse import urlencode
        q = urlencode({
            "service_id": settings.CLICK_SERVICE_ID, "merchant_id": settings.CLICK_MERCHANT_ID,
            "amount": f"{amount:.2f}", "transaction_param": contract.id, "return_url": return_url,
        })
        return {"demo": False, "url": f"https://my.click.uz/services/pay?{q}"}
    return {"demo": False, "url": None}


# ---------------- DEMO ----------------
@api_view(["POST"])
def demo_confirm(request, payment_id):
    p = Payment.objects.select_related("contract").filter(id=payment_id, is_demo=True).first()
    token = request.data.get("c") or request.query_params.get("c")
    if not p or str(p.contract.token) != str(token):
        return Response({"detail": "not found"}, status=404)
    if p.status == Payment.ST_PAID:
        return Response({"ok": True, "already": True})
    register_payment(p.contract, p.amount, p.method, is_demo=True, payment=p, note="DEMO")
    return Response({"ok": True, "demo": True})


@api_view(["GET"])
def demo_info(request, payment_id):
    p = Payment.objects.select_related("contract__seller", "contract__application").filter(id=payment_id, is_demo=True).first()
    token = request.query_params.get("c")
    if not p or str(p.contract.token) != str(token):
        return Response({"detail": "not found"}, status=404)
    return Response({
        "payment_id": p.id, "method": p.method, "amount": str(p.amount), "status": p.status,
        "contract": p.contract.number, "seller": p.contract.seller.name,
        "order_token": str(p.contract.application.token),
    })


# ---------------- PAYME ----------------
def _now_ms():
    return int(time.time() * 1000)


def _pm_err(rid, code, msg, data=None):
    err = {"code": code, "message": {"uz": msg, "ru": msg, "en": msg}}
    if data:
        err["data"] = data
    return JsonResponse({"jsonrpc": "2.0", "id": rid, "error": err})


def _pm_ok(rid, result):
    return JsonResponse({"jsonrpc": "2.0", "id": rid, "result": result})


def _pm_auth(request):
    h = request.META.get("HTTP_AUTHORIZATION", "")
    if not h.startswith("Basic "):
        return False
    try:
        login, key = base64.b64decode(h[6:]).decode().split(":", 1)
    except Exception:
        return False
    return key == settings.PAYME_KEY


PAYME_TIMEOUT_MS = 12 * 3600 * 1000


@csrf_exempt
def payme_endpoint(request):
    import json

    try:
        body = json.loads(request.body or b"{}")
    except ValueError:
        return _pm_err(None, -32700, "Parse error")
    rid = body.get("id")
    if request.method != "POST":
        return _pm_err(rid, -32300, "POST only")
    if not payme_enabled() or not _pm_auth(request):
        return _pm_err(rid, -32504, "Unauthorized")
    method, params = body.get("method"), body.get("params") or {}
    handler = {
        "CheckPerformTransaction": _pm_check_perform,
        "CreateTransaction": _pm_create,
        "PerformTransaction": _pm_perform,
        "CancelTransaction": _pm_cancel,
        "CheckTransaction": _pm_check,
        "GetStatement": _pm_statement,
    }.get(method)
    if not handler:
        return _pm_err(rid, -32601, "Method not found")
    return handler(rid, params)


def _pm_contract(rid, params):
    cid = (params.get("account") or {}).get("contract_id")
    c = Contract.objects.filter(id=cid).first() if str(cid or "").isdigit() else None
    if not c or c.status == Contract.ST_CANCELLED:
        return None, _pm_err(rid, -31050, "Contract not found", "contract_id")
    if c.due_amount <= 0:
        return None, _pm_err(rid, -31051, "Already paid", "contract_id")
    if int(params.get("amount", 0)) != int(c.due_amount * 100):
        return None, _pm_err(rid, -31001, "Incorrect amount")
    return c, None


def _pm_check_perform(rid, params):
    c, err = _pm_contract(rid, params)
    return err or _pm_ok(rid, {"allow": True})


@transaction.atomic
def _pm_create(rid, params):
    txn = Payment.objects.filter(method="payme", provider_txn_id=params.get("id")).first()
    if txn:
        if txn.provider_state != 1:
            return _pm_err(rid, -31008, "Cannot perform")
        if _now_ms() - txn.provider_create_time > PAYME_TIMEOUT_MS:
            txn.provider_state, txn.provider_reason, txn.provider_cancel_time = -1, 4, _now_ms()
            txn.status = Payment.ST_CANCELLED
            txn.save()
            return _pm_err(rid, -31008, "Timeout")
        return _pm_ok(rid, {"create_time": txn.provider_create_time, "transaction": str(txn.id), "state": 1})
    c, err = _pm_contract(rid, params)
    if err:
        return err
    if Payment.objects.filter(contract=c, method="payme", provider_state=1).exists():
        return _pm_err(rid, -31050, "Another transaction in progress", "contract_id")
    txn = Payment.objects.create(
        contract=c, method="payme", amount=Decimal(params["amount"]) / 100, provider_txn_id=params["id"],
        provider_state=1, provider_create_time=int(params.get("time") or _now_ms()),
    )
    return _pm_ok(rid, {"create_time": txn.provider_create_time, "transaction": str(txn.id), "state": 1})


@transaction.atomic
def _pm_perform(rid, params):
    txn = Payment.objects.select_for_update().filter(method="payme", provider_txn_id=params.get("id")).first()
    if not txn:
        return _pm_err(rid, -31003, "Transaction not found")
    if txn.provider_state == 2:
        return _pm_ok(rid, {"transaction": str(txn.id), "perform_time": txn.provider_perform_time, "state": 2})
    if txn.provider_state != 1:
        return _pm_err(rid, -31008, "Cannot perform")
    if _now_ms() - txn.provider_create_time > PAYME_TIMEOUT_MS:
        txn.provider_state, txn.provider_reason, txn.provider_cancel_time = -1, 4, _now_ms()
        txn.status = Payment.ST_CANCELLED
        txn.save()
        return _pm_err(rid, -31008, "Timeout")
    txn.provider_state, txn.provider_perform_time = 2, _now_ms()
    txn.save()
    register_payment(txn.contract, txn.amount, "payme", payment=txn)
    return _pm_ok(rid, {"transaction": str(txn.id), "perform_time": txn.provider_perform_time, "state": 2})


@transaction.atomic
def _pm_cancel(rid, params):
    txn = Payment.objects.select_for_update().filter(method="payme", provider_txn_id=params.get("id")).first()
    if not txn:
        return _pm_err(rid, -31003, "Transaction not found")
    if txn.provider_state in (-1, -2):
        return _pm_ok(rid, {"transaction": str(txn.id), "cancel_time": txn.provider_cancel_time, "state": txn.provider_state})
    c = txn.contract
    if txn.provider_state == 2 and c.status in (Contract.ST_SHIPPED, Contract.ST_DONE):
        return _pm_err(rid, -31007, "Order completed, cannot cancel")
    was_paid = txn.provider_state == 2
    txn.provider_state = -2 if was_paid else -1
    txn.provider_reason = params.get("reason")
    txn.provider_cancel_time = _now_ms()
    txn.status = Payment.ST_CANCELLED
    txn.save()
    if was_paid:
        c.paid_amount = sum((p.amount for p in c.payments.filter(status=Payment.ST_PAID)), Decimal("0"))
        if c.status == Contract.ST_PAID:
            c.status = Contract.ST_ACTIVE
        c.save()
        log(c.application, "refund", f"payme: {txn.amount}")
    return _pm_ok(rid, {"transaction": str(txn.id), "cancel_time": txn.provider_cancel_time, "state": txn.provider_state})


def _pm_check(rid, params):
    txn = Payment.objects.filter(method="payme", provider_txn_id=params.get("id")).first()
    if not txn:
        return _pm_err(rid, -31003, "Transaction not found")
    return _pm_ok(rid, {
        "create_time": txn.provider_create_time, "perform_time": txn.provider_perform_time,
        "cancel_time": txn.provider_cancel_time, "transaction": str(txn.id), "state": txn.provider_state,
        "reason": txn.provider_reason,
    })


def _pm_statement(rid, params):
    qs = Payment.objects.filter(method="payme", provider_create_time__gte=params.get("from", 0),
                                provider_create_time__lte=params.get("to", 0)).exclude(provider_txn_id="")
    return _pm_ok(rid, {"transactions": [{
        "id": t.provider_txn_id, "time": t.provider_create_time, "amount": int(t.amount * 100),
        "account": {"contract_id": t.contract_id}, "create_time": t.provider_create_time,
        "perform_time": t.provider_perform_time, "cancel_time": t.provider_cancel_time,
        "transaction": str(t.id), "state": t.provider_state, "reason": t.provider_reason,
    } for t in qs]})


# ---------------- CLICK ----------------
def _click_sign_ok(d, with_prepare):
    parts = [d.get("click_trans_id", ""), d.get("service_id", ""), settings.CLICK_SECRET_KEY, d.get("merchant_trans_id", "")]
    if with_prepare:
        parts.append(d.get("merchant_prepare_id", ""))
    parts += [d.get("amount", ""), d.get("action", ""), d.get("sign_time", "")]
    return hashlib.md5("".join(str(p) for p in parts).encode()).hexdigest() == d.get("sign_string")


def _click_resp(d, error, note, **extra):
    out = {"click_trans_id": d.get("click_trans_id"), "merchant_trans_id": d.get("merchant_trans_id"),
           "error": error, "error_note": note}
    out.update(extra)
    return JsonResponse(out)


@csrf_exempt
@transaction.atomic
def click_prepare(request):
    d = request.POST.dict()
    if not click_enabled() or not _click_sign_ok(d, False):
        return _click_resp(d, -1, "SIGN CHECK FAILED!")
    if str(d.get("action")) != "0":
        return _click_resp(d, -3, "Action not found")
    c = Contract.objects.filter(id=d.get("merchant_trans_id")).first() if str(d.get("merchant_trans_id", "")).isdigit() else None
    if not c or c.status == Contract.ST_CANCELLED:
        return _click_resp(d, -5, "Contract does not exist")
    if c.due_amount <= 0:
        return _click_resp(d, -4, "Already paid")
    if Decimal(d.get("amount", "0")) != c.due_amount:
        return _click_resp(d, -2, "Incorrect parameter amount")
    p = Payment.objects.create(contract=c, method="click", amount=c.due_amount, provider_txn_id=d.get("click_trans_id", ""))
    return _click_resp(d, 0, "Success", merchant_prepare_id=p.id)


@csrf_exempt
@transaction.atomic
def click_complete(request):
    d = request.POST.dict()
    if not click_enabled() or not _click_sign_ok(d, True):
        return _click_resp(d, -1, "SIGN CHECK FAILED!")
    if str(d.get("action")) != "1":
        return _click_resp(d, -3, "Action not found")
    p = Payment.objects.select_for_update().filter(id=d.get("merchant_prepare_id"), method="click").first()
    if not p:
        return _click_resp(d, -6, "Transaction does not exist")
    if p.status == Payment.ST_PAID:
        return _click_resp(d, -4, "Already paid", merchant_confirm_id=p.id)
    if p.status == Payment.ST_CANCELLED:
        return _click_resp(d, -9, "Transaction cancelled")
    if Decimal(d.get("amount", "0")) != p.amount:
        return _click_resp(d, -2, "Incorrect parameter amount")
    if int(d.get("error", 0)) < 0:
        p.status = Payment.ST_CANCELLED
        p.save()
        return _click_resp(d, -9, "Transaction cancelled")
    register_payment(p.contract, p.amount, "click", payment=p)
    return _click_resp(d, 0, "Success", merchant_confirm_id=p.id)
