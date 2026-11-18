#!/bin/sh
cd "$(dirname "$0")"
if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi
if [ -z "${SECRET_KEY:-}" ]; then
  echo "Задайте SECRET_KEY в .env (случайная строка от 32 символов) и запустите снова."
  exit 1
fi
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export APP_ENV=development
uvicorn backend.app:app --host 127.0.0.1 --port 8000
