FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY docker-entrypoint.sh ./docker-entrypoint.sh
RUN chmod +x ./docker-entrypoint.sh
COPY backend ./backend
COPY alembic.ini .
COPY migrations ./migrations
COPY index.html styles.css app.js privacy.html terms.html ./
EXPOSE 10000
CMD ["./docker-entrypoint.sh"]
