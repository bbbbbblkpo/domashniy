from datetime import datetime, date, timezone
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="Сотрудник")
    employee_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    employee = relationship("Employee", foreign_keys=[employee_id])
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

class Employee(Base):
    __tablename__ = "employees"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class Shift(Base):
    __tablename__ = "shifts"
    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    shift_type: Mapped[str] = mapped_column(String(10))
    cashier_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    hall_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True)

class Advance(Base):
    __tablename__ = "advances"
    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    amount: Mapped[float] = mapped_column(Numeric(12,2))
    comment: Mapped[str] = mapped_column(String(500), default="")

class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_date: Mapped[date] = mapped_column(Date, index=True)
    supplier: Mapped[str] = mapped_column(String(160))
    items_text: Mapped[str] = mapped_column(Text)
    amount: Mapped[float] = mapped_column(Numeric(12,2))
    delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Новый")
    comment: Mapped[str] = mapped_column(String(1000), default="")
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))

class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(String(500))

class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    csrf_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)

class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    ip: Mapped[str] = mapped_column(String(64))
    username: Mapped[str] = mapped_column(String(80))
    at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    succeeded: Mapped[bool] = mapped_column(Boolean, default=False)

class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    action: Mapped[str] = mapped_column(String(500))
    ip: Mapped[str] = mapped_column(String(64))
