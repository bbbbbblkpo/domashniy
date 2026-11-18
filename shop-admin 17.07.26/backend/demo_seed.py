"""Seed a disposable SQLite database with fictional demo data only."""

from datetime import date
import logging
import os

from sqlalchemy.orm import Session

from .db import Base, DEMO_MODE, SessionLocal, engine
from .models import Advance, AuditLog, Employee, Order, Setting, Shift, User
from .security import password_hash

log = logging.getLogger(__name__)

EMPLOYEE_NAMES = (
    "Азамат", "Айбек", "Айгерим", "Аяу", "Балу",
    "Венера", "Жанай", "Жанель", "Жулдыз", "Инжу",
)

# Fourteen shifts, two positions per shift: 28 employee-shift outputs total.
SHIFT_PAIRS = (
    ("Жулдыз", "Балу"), ("Айгерим", "Венера"),
    ("Жулдыз", "Инжу"), ("Балу", "Айбек"),
    ("Аяу", "Инжу"), ("Балу", "Венера"),
    ("Аяу", "Инжу"), ("Жулдыз", "Азамат"),
    ("Жанай", "Жанель"), ("Жулдыз", "Балу"),
    ("Жанай", "Жанель"), ("Аяу", "Инжу"),
    ("Балу", "Азамат"), ("Инжу", "Балу"),
)

DEMO_USERS = (
    ("demo-owner", "Владелец", "DEMO_OWNER_PASSWORD", None),
    ("demo-admin", "Администратор", "DEMO_ADMIN_PASSWORD", None),
    ("demo-employee", "Сотрудник", "DEMO_EMPLOYEE_PASSWORD", "Азамат"),
)


def seed_demo_records(db: Session) -> None:
    """Insert the canonical fictitious employees, logins, shifts, debts and orders."""
    employees = {e.name: e for e in db.query(Employee).all()}
    for name in EMPLOYEE_NAMES:
        employee = employees.get(name)
        if employee is None:
            employee = Employee(name=name, active=True)
            db.add(employee)
            employees[name] = employee
        else:
            employee.active = True
    db.flush()

    users: dict[str, User] = {}
    for username, role, password_key, employee_name in DEMO_USERS:
        user = db.query(User).filter_by(username=username).first()
        if user is None:
            user = User(username=username, role=role, active=True)
            db.add(user)
        user.role = role
        user.active = True
        user.must_change_password = False
        user.employee_id = employees[employee_name].id if employee_name else None
        user.password_hash = password_hash.hash(os.environ[password_key])
        users[username] = user
    db.flush()

    if db.query(Shift).count() == 0:
        for index, (cashier, hall) in enumerate(SHIFT_PAIRS):
            db.add(Shift(
                date=date(2026, 11, 16 + index // 2),
                shift_type="День" if index % 2 == 0 else "Ночь",
                cashier_id=employees[cashier].id,
                hall_id=employees[hall].id,
            ))

    if db.query(Advance).count() == 0:
        db.add_all([
            Advance(date=date(2026, 11, 18), employee_id=employees["Азамат"].id,
                    amount=-15000, comment="Демо-аванс"),
            Advance(date=date(2026, 11, 20), employee_id=employees["Жулдыз"].id,
                    amount=-8000, comment="Демо-долг"),
        ])

    rate = db.query(Setting).filter_by(key="rate_per_shift").first()
    if rate is None:
        db.add(Setting(key="rate_per_shift", value="10000"))
    else:
        rate.value = "10000"

    if db.query(Order).count() == 0:
        owner = users["demo-owner"]
        db.add_all([
            Order(order_date=date(2026, 11, 17), supplier="Демо-поставщик продуктов",
                  items_text="Молоко, хлеб, крупы", amount=68500,
                  delivery_date=date(2026, 11, 19), status="Заказан",
                  comment="Вымышленный заказ для показа", created_by=owner.id),
            Order(order_date=date(2026, 11, 18), supplier="Учебный склад напитков",
                  items_text="Вода, соки", amount=42300,
                  delivery_date=date(2026, 11, 21), status="Новый",
                  comment="Вымышленный заказ для показа", created_by=owner.id),
        ])
    db.flush()


def reset_demo_data(db: Session) -> None:
    """Reset business data while keeping user accounts and active sessions."""
    for model in (Shift, Advance, Order, AuditLog, Setting):
        db.query(model).delete(synchronize_session=False)
    # Employees outside the built-in fictional set are retained for existing user links,
    # but hidden from scheduling and payroll after reset.
    db.query(Employee).filter(~Employee.name.in_(EMPLOYEE_NAMES)).update(
        {Employee.active: False}, synchronize_session=False
    )
    seed_demo_records(db)


def initialize_demo_database() -> None:
    if not DEMO_MODE:
        raise RuntimeError("Для заполнения демо-базы задайте DEMO_MODE=true")
    # This database path is selected in db.py and is always SQLite in DEMO_MODE.
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_demo_records(db)
        db.commit()
    log.info("Демо-база SQLite пересоздана: только вымышленные данные, 10 сотрудников")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    initialize_demo_database()
