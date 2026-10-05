#!/usr/bin/env bash
set -o errexit

python manage.py migrate_schemas --noinput

python manage.py all_tenants_command clearsessions

exec "$@"
