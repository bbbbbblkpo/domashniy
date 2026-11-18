import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DEMO_MODE = os.getenv("DEMO_MODE", "false").strip().lower() in {"1", "true", "yes", "on"}

if DEMO_MODE:
    demo_password_keys = ("DEMO_OWNER_PASSWORD", "DEMO_ADMIN_PASSWORD", "DEMO_EMPLOYEE_PASSWORD")
    missing = [key for key in demo_password_keys if not os.getenv(key)]
    if missing:
        raise RuntimeError(
            "DEMO_MODE включен, но не заданы переменные окружения: " + ", ".join(missing)
        )
    weak = [key for key in demo_password_keys if len(os.environ[key]) < 10]
    if weak:
        raise RuntimeError(
            "Пароли демо-аккаунтов должны содержать не менее 10 символов: " + ", ".join(weak)
        )
    if len({os.environ[key] for key in demo_password_keys}) != len(demo_password_keys):
        raise RuntimeError("Для трёх демо-аккаунтов задайте разные пароли")

    # Demo must never connect to, import from, or modify the application's normal DB.
    demo_db_path = Path(os.getenv("DEMO_DB_PATH", "/tmp/smena-demo.sqlite3")).expanduser().resolve()
    demo_db_path.parent.mkdir(parents=True, exist_ok=True)
    DATABASE_URL = f"sqlite:///{demo_db_path}"
    os.environ["DATABASE_URL"] = DATABASE_URL
else:
    DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./data.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
