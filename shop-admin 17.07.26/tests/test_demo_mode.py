import os
import secrets
import subprocess
import sys


DEMO_PASSWORD_KEYS = (
    "DEMO_OWNER_PASSWORD",
    "DEMO_ADMIN_PASSWORD",
    "DEMO_EMPLOYEE_PASSWORD",
)


def test_demo_mode_refuses_to_start_without_demo_passwords(tmp_path):
    env = os.environ.copy()
    env["DEMO_MODE"] = "true"
    env["DEMO_DB_PATH"] = str(tmp_path / "missing-passwords.sqlite3")
    env["APP_ENV"] = "development"
    for key in DEMO_PASSWORD_KEYS:
        env.pop(key, None)

    result = subprocess.run(
        [sys.executable, "-c", "import backend.app"],
        cwd=os.getcwd(), env=env, capture_output=True, text=True,
    )

    assert result.returncode != 0
    assert "DEMO_MODE включен" in result.stderr
    assert all(key in result.stderr for key in DEMO_PASSWORD_KEYS)


def test_demo_seed_has_fake_accounts_and_employee_scope(tmp_path):
    env = os.environ.copy()
    env.update({
        "DEMO_MODE": "true",
        "DEMO_DB_PATH": str(tmp_path / "seeded-demo.sqlite3"),
        "APP_ENV": "production",
        "COOKIE_SECURE": "true",
        "SECRET_KEY": secrets.token_urlsafe(32),
        **{key: secrets.token_urlsafe(24) for key in DEMO_PASSWORD_KEYS},
    })
    source = r'''
from backend.demo_seed import initialize_demo_database
initialize_demo_database()
import os
from datetime import date
from decimal import Decimal
from backend.db import SessionLocal
from backend.models import Advance, Employee, Order, Shift, User
from backend.security import password_hash
from backend.services.payroll import calculate_payroll
with SessionLocal() as db:
    people = db.query(Employee).count()
    shifts = db.query(Shift).count()
    advances = db.query(Advance).count()
    orders = db.query(Order).count()
    accounts = db.query(User).all()
    summary = calculate_payroll(db, date(2026,11,16), date(2026,11,22), Decimal("10000"))
    gross_fund = sum(row["shifts"] for row in summary.values()) * Decimal("10000")
    assert (people, shifts, advances, orders) == (10, 14, 2, 2)
    assert sum(row["shifts"] for row in summary.values()) == 28
    assert gross_fund == Decimal("280000")
    assert len(accounts) == 3
    password_keys = ("DEMO_OWNER_PASSWORD", "DEMO_ADMIN_PASSWORD", "DEMO_EMPLOYEE_PASSWORD")
    assert all(password_hash.verify(os.environ[key], account.password_hash) for account, key in zip(accounts, password_keys))
    assert all(os.environ[key] != account.password_hash for account, key in zip(accounts, password_keys))
from fastapi.testclient import TestClient
from backend.app import app

def session(username, password):
    client = TestClient(app, base_url="https://demo.test")
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return client

import os
owner = session("demo-owner", os.environ["DEMO_OWNER_PASSWORD"])
assert owner.get("/api/config").json() == {"demo_mode": True}
assert len(owner.get("/api/employees").json()) == 10
assert owner.get("/api/shifts", params={"start":"2026-11-16", "end":"2026-11-22"}).status_code == 200
assert owner.get("/api/backup").status_code == 403
csrf = owner.cookies.get("shop_csrf")
assert owner.post("/api/demo/reset", headers={"x-csrf-token":csrf}, json={}).status_code == 200

admin = session("demo-admin", os.environ["DEMO_ADMIN_PASSWORD"])
assert admin.get("/api/orders").status_code == 200
assert admin.get("/api/users").status_code == 403

employee = session("demo-employee", os.environ["DEMO_EMPLOYEE_PASSWORD"])
payroll = employee.get("/api/payroll", params={"start":"2026-11-16", "end":"2026-11-22"})
assert payroll.status_code == 200 and payroll.json()["employee_id"] == 1
assert employee.get("/api/payroll", params={"start":"2026-11-16", "end":"2026-11-22", "employee_id":2}).status_code == 403
assert employee.get("/api/shifts", params={"start":"2026-11-16", "end":"2026-11-22"}).status_code == 403
assert employee.get("/api/advances", params={"start":"2026-11-16", "end":"2026-11-22"}).status_code == 403
assert employee.get("/api/orders").status_code == 403
csrf = employee.cookies.get("shop_csrf")
assert employee.post("/api/auth/logout", headers={"x-csrf-token":csrf}).status_code == 200
assert employee.get("/api/payroll", params={"start":"2026-11-16", "end":"2026-11-22"}).status_code == 401
'''
    result = subprocess.run(
        [sys.executable, "-c", source],
        cwd=os.getcwd(), env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
