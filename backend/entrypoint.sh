#!/bin/sh
set -e
python manage.py migrate --noinput
# Birinchi ishga tushishda katalog + 40 ta muassasa logini (keyingi startlarda tegmaydi)
python manage.py seed --if-empty --credentials /tmp/credentials.xlsx
exec gunicorn config.wsgi:application -b 0.0.0.0:8000 -w ${GUNICORN_WORKERS:-3} --timeout 90 --access-logfile -
