#!/usr/bin/env bash
set -o errexit

python manage.py migrar_esquemas

python manage.py limpiar_sesiones

exec "$@"
