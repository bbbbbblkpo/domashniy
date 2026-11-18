from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator

class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)

class OwnerSetupIn(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=10, max_length=200)

class UserCreateIn(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=10, max_length=200)
    role: str
    employee_id: int | None = None
    @field_validator('role')
    @classmethod
    def allowed_role(cls, value):
        if value not in {'Владелец','Администратор','Сотрудник'}: raise ValueError('Недопустимая роль')
        return value

class ShiftIn(BaseModel):
    date: date
    shift_type: str
    cashier_id: int
    hall_id: int | None = None
    confirm_warnings: bool = False
    @field_validator('shift_type')
    @classmethod
    def valid_type(cls,v):
        if v not in {'День','Ночь'}: raise ValueError('Смена должна быть День или Ночь')
        return v

class AdvanceIn(BaseModel):
    date: date
    employee_id: int
    amount: Decimal
    comment: str = Field(default='', max_length=500)

class OrderIn(BaseModel):
    order_date: date
    supplier: str = Field(min_length=1,max_length=160)
    items_text: str = Field(min_length=1,max_length=10000)
    amount: Decimal = Field(ge=0)
    delivery_date: date | None = None
    status: str = 'Новый'
    comment: str = Field(default='',max_length=1000)
    @field_validator('status')
    @classmethod
    def valid_status(cls,v):
        if v not in {'Новый','Заказан','Доставлен','Оплачен','Отменён'}: raise ValueError('Некорректный статус заказа')
        return v

class PasswordChangeIn(BaseModel):
    current_password: str = Field(min_length=1,max_length=200)
    new_password: str = Field(min_length=10,max_length=200)

class EmployeeIn(BaseModel):
    name: str = Field(min_length=1,max_length=120)

class RateIn(BaseModel):
    rate: Decimal = Field(ge=0,le=10000000)

class RepaymentIn(BaseModel):
    date: date
    employee_id: int
    amount: Decimal = Field(gt=0)
    comment: str = Field(default='Погашение',max_length=500)
