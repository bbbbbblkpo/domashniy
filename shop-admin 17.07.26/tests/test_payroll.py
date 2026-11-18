from datetime import date
from decimal import Decimal
from backend.db import Base
from backend.models import Employee, Shift, Advance
from backend.services.payroll import calculate_payroll
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

def test_demo_week_totals_and_same_employee_once():
    eng=create_engine('sqlite:///:memory:');Base.metadata.create_all(eng)
    pairs=[('Жулдыз','Балу'),('Айгерим','Венера'),('Жулдыз','Инжу'),('Балу','Айбек'),('Аяу','Инжу'),('Балу','Венера'),('Аяу','Инжу'),('Жулдыз','Азамат'),('Жанай','Жанель'),('Жулдыз','Балу'),('Жанай','Жанель'),('Аяу','Инжу'),('Балу','Азамат'),('Инжу','Балу')]
    with Session(eng) as db:
        names=sorted({n for p in pairs for n in p}); emps={n:Employee(name=n) for n in names};db.add_all(emps.values());db.flush()
        for i,(cashier,hall) in enumerate(pairs):
            day=date(2026,11,16+i//2);typ='День' if i%2==0 else 'Ночь'
            db.add(Shift(date=day,shift_type=typ,cashier_id=emps[cashier].id,hall_id=emps[hall].id))
        db.flush();rows=calculate_payroll(db,date(2026,11,16),date(2026,11,22),Decimal(10000))
        assert sum(x['shifts'] for x in rows.values())==28
        assert sum(x['salary'] for x in rows.values())==Decimal(280000)
        db.add(Advance(date=date(2026,11,18),employee_id=emps['Балу'].id,amount=-15000));db.flush()
        rows=calculate_payroll(db,date(2026,11,16),date(2026,11,22),Decimal(10000))
        assert rows[emps['Балу'].id]['salary']==Decimal(45000)

def test_night_shift_start_date_controls_payroll_week():
    eng=create_engine('sqlite:///:memory:');Base.metadata.create_all(eng)
    with Session(eng) as db:
        e=Employee(name='Ночная смена');db.add(e);db.flush()
        db.add(Shift(date=date(2026,11,16),shift_type='Ночь',cashier_id=e.id,hall_id=None));db.flush()
        rows=calculate_payroll(db,date(2026,11,16),date(2026,11,22),Decimal(10000))
        assert rows[e.id]['shifts']==1 and rows[e.id]['salary']==Decimal(10000)
        next_week=calculate_payroll(db,date(2026,11,17),date(2026,11,23),Decimal(10000))
        assert e.id not in next_week

def test_shift_warnings_for_day_night_and_next_day_rest():
    from backend.services.payroll import shift_warnings
    from backend.models import Shift
    d=date(2026,11,16)
    day=Shift(date=d,shift_type='День',cashier_id=1,hall_id=2)
    night_same=Shift(date=d,shift_type='Ночь',cashier_id=1,hall_id=3)
    assert shift_warnings([day],night_same)[0]['code']=='same_date_day_night'
    night=Shift(date=d,shift_type='Ночь',cashier_id=1,hall_id=None)
    next_day=Shift(date=date(2026,11,17),shift_type='День',cashier_id=1,hall_id=None)
    assert shift_warnings([night],next_day)[0]['code']=='no_rest'

def test_single_night_is_one_output():
    eng=create_engine('sqlite:///:memory:');Base.metadata.create_all(eng)
    with Session(eng) as db:
        e=Employee(name='Одна ночь');db.add(e);db.flush()
        db.add(Shift(date=date(2026,11,16),shift_type='Ночь',cashier_id=e.id,hall_id=e.id));db.flush()
        assert calculate_payroll(db,date(2026,11,16),date(2026,11,16),Decimal(10000))[e.id]['shifts']==1

def test_week_boundary_0030_almaty_is_monday():
    from datetime import datetime, timezone
    from backend.services.timezone import week_bounds
    # 2026-11-15 19:30 UTC is 2026-11-16 00:30 in Almaty.
    start,end=week_bounds(datetime(2026,11,15,19,30,tzinfo=timezone.utc))
    assert start==date(2026,11,16) and end==date(2026,11,22)
