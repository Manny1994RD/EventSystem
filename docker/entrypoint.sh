#!/bin/sh
set -e
python manage.py migrate --noinput
python manage.py setup_initial
python manage.py make_previews
exec "$@"
