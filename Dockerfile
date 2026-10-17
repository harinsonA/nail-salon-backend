FROM python:3.12.8-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Locale en español, requerido por format_full_date() (apps/common/utils/dates.py)
RUN apt-get update && apt-get install -y --no-install-recommends locales \
    && localedef -i es_CL -f UTF-8 es_CL.UTF-8 \
    && rm -rf /var/lib/apt/lists/*
ENV LANG=es_CL.UTF-8 \
    LC_ALL=es_CL.UTF-8

WORKDIR /app


FROM base AS deps

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Capa de dependencias separada del código: mientras no cambie
# requirements.txt, los rebuilds reutilizan la capa cacheada de pip
COPY requirements.txt .
RUN pip install -r requirements.txt


FROM deps AS app

COPY manage.py entrypoint.sh ./
COPY nail_salon_api/ nail_salon_api/
COPY apps/ apps/
COPY dashboard/ dashboard/
COPY templates/ templates/
COPY static/ static/

RUN SECRET_KEY=solo-para-collectstatic python manage.py collectstatic --no-input \
    && chmod +x entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
# Render inyecta PORT en runtime; en local y CI se usa 8000
CMD ["sh", "-c", "exec gunicorn nail_salon_api.wsgi:application --bind 0.0.0.0:${PORT:-8000}"]


FROM app AS test

COPY tests/ tests/


FROM app AS prod
