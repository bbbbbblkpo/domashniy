# Смены

Локальная панель учета находится в `index.html`, `styles.css`, `app.js`. Серверная защищенная основа находится в `backend/`.

Локальный запуск API: установите Python 3.11+, скопируйте `.env.example` в `.env`, задайте секреты, установите зависимости командой `pip install -r requirements.txt`, затем запустите `uvicorn backend.app:app --reload`. Для контейнерного деплоя читайте [DEPLOY.md](DEPLOY.md).

Первого владельца создайте POST-запросом `/api/auth/setup-owner` один раз (логин и пароль не менее 10 символов). Для тестов в Docker: `docker run --rm -v "$PWD:/workspace" -w /workspace python:3.12-slim sh -lc "pip install -r requirements.txt && pytest -vv"`. Перед публичным запуском изучите [DEPLOY.md](DEPLOY.md), заполните юридические шаблоны `privacy.html` и `terms.html`, проверьте лицензии в `LICENSE`/`THIRD_PARTY_NOTICES.md` и используйте только HTTPS.

### Закрытая демо-версия

Для демо используйте только вымышленные данные. Скопируйте `.env.example` в `.env`, придумайте три разных пароля длиной не менее 10 символов для `DEMO_OWNER_PASSWORD`, `DEMO_ADMIN_PASSWORD` и `DEMO_EMPLOYEE_PASSWORD`, задайте случайный `SECRET_KEY`, затем запустите:

```sh
docker compose -f docker-compose.demo.yml up --build
```

Демо открывается на `http://localhost:18080`. При каждом старте отдельная SQLite-база пересоздаётся из демонстрационного набора. Демо никогда не подключается к основной БД; импорт и скачивание копии отключены. Пароли не записывайте в код и не добавляйте `.env` в Git.

Инструкция для временной ссылки Render: [DEPLOY_DEMO.md](DEPLOY_DEMO.md). Она не публикует приложение сама.

Сбросить локальную тестовую базу и контейнерные тома: `docker compose down -v`. Команда удаляет PostgreSQL данные основного Compose-стека без восстановления. Для локальной одноразовой демо-базы остановите `docker compose -f docker-compose.demo.yml down`; данные находятся только внутри контейнера и создаются заново при старте.
