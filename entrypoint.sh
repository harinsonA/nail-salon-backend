#!/usr/bin/env bash
set -o errexit

python manage.py migrate --no-input

python manage.py clearsessions

exec "$@"
