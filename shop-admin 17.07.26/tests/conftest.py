import os
import secrets
os.environ.setdefault('DATABASE_URL',f"sqlite:////tmp/smena-tests-{secrets.token_hex(8)}.db")
os.environ.setdefault('APP_ENV','development')
os.environ.setdefault('COOKIE_SECURE','false')
os.environ.setdefault('SECRET_KEY',secrets.token_urlsafe(32))

OWNER_PASSWORD = secrets.token_urlsafe(18)
ADMIN_PASSWORD = secrets.token_urlsafe(18)
STAFF_PASSWORD = secrets.token_urlsafe(18)
NEW_USER_PASSWORD = secrets.token_urlsafe(18)
RESET_PASSWORD = secrets.token_urlsafe(18)
UPDATED_PASSWORD = secrets.token_urlsafe(18)
TEMP_PASSWORD = secrets.token_urlsafe(18)
PERMANENT_PASSWORD = secrets.token_urlsafe(18)
WRONG_PASSWORD = secrets.token_urlsafe(18)
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.db import Base, engine, SessionLocal
from backend.models import User, Employee
from backend.security import password_hash

@pytest.fixture
def client():
    Base.metadata.drop_all(engine);Base.metadata.create_all(engine)
    with SessionLocal() as db:
        emp=Employee(name='Сотрудник А');other=Employee(name='Сотрудник Б');db.add_all([emp,other]);db.flush()
        owner=User(username='owner',password_hash=password_hash.hash(OWNER_PASSWORD),role='Владелец')
        admin=User(username='admin',password_hash=password_hash.hash(ADMIN_PASSWORD),role='Администратор')
        staff=User(username='staff',password_hash=password_hash.hash(STAFF_PASSWORD),role='Сотрудник',employee_id=emp.id)
        db.add_all([owner,admin,staff]);db.commit()
    with TestClient(app) as c: yield c
    Base.metadata.drop_all(engine)

def login(client,username,password):
    return client.post('/api/auth/login',json={'username':username,'password':password})

def csrf(client): return {'x-csrf-token':client.cookies.get('shop_csrf','')}
