#!/bin/sh
set -e
python manage.py migrate --noinput
# Birinchi ishga tushishda katalog + 40 ta muassasa logini (keyingi startlarda tegmaydi)
python manage.py seed --if-empty --credentials /tmp/credentials.xlsx
# Rasmsiz mahsulotlarga namunaviy (AI) rasm — haqiqiy surat yuklanganlarga tegmaydi
python manage.py load_sample_images || true
# Xususiyatlar lug'ati (yangi xususiyat/variantlar qo'shiladi, operator tahrirlariga tegmaydi) + bo'sh kartochkalarni to'ldirish
python manage.py load_attributes || true
python manage.py analyze_images || true
# IKPU (MXIK) tavsiyasi — tasnif.soliq.uz orqali, bir marta, fonda (start sekinlashmasin)
(python manage.py suggest_ikpu --once > /tmp/suggest_ikpu.log 2>&1 &) || true
exec gunicorn config.wsgi:application -b 0.0.0.0:8000 -w ${GUNICORN_WORKERS:-3} --timeout 90 --access-logfile -
