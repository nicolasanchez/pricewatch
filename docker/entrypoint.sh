#!/bin/sh
# Prepara la base de datos y los estáticos antes de arrancar la web.
set -e
python manage.py migrate --noinput
python manage.py collectstatic --noinput >/dev/null
exec "$@"
