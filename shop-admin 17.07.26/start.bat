@echo off
cd /d "%~dp0"
if not exist .venv python -m venv .venv
call .venv\Scripts\activate
pip install -r requirements.txt
set APP_ENV=development
if "%SECRET_KEY%"=="" echo Задайте SECRET_KEY в переменных среды (случайная строка от 32 символов) и запустите снова.& exit /b 1
start http://127.0.0.1:8000
uvicorn backend.app:app --host 127.0.0.1 --port 8000
