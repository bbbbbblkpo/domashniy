#!/bin/sh
set -eu

if [ "${APP_ENV:-production}" != "development" ] && [ -z "${SECRET_KEY:-}" ]; then
  echo "Ошибка запуска: не задан SECRET_KEY в переменных окружения." >&2
  exit 1
fi

case "${DEMO_MODE:-false}" in
  1|true|TRUE|yes|YES|on|ON)
    python -m backend.demo_seed
    ;;
esac

exec gunicorn backend.app:app -k uvicorn.workers.UvicornWorker -w 1 -b "0.0.0.0:${PORT:-10000}"
