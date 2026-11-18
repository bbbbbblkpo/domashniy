from collections import defaultdict
from datetime import date
from decimal import Decimal
from sqlalchemy import or_
from sqlalchemy.orm import Session
from ..models import Advance, Shift

def calculate_payroll(db: Session, start: date, end: date, rate: Decimal):
    """Count one employee once per shift row even when listed as cashier and hall."""
    counts = defaultdict(int)
    shifts = db.query(Shift).filter(Shift.date >= start, Shift.date <= end).all()
    for shift in shifts:
        for employee_id in {shift.cashier_id, shift.hall_id} - {None}:
            counts[employee_id] += 1
    sums = defaultdict(Decimal)
    for advance in db.query(Advance).filter(Advance.date >= start, Advance.date <= end).all():
        sums[advance.employee_id] += Decimal(str(advance.amount))
    rows = {}
    for eid in set(counts) | set(sums):
        n = counts[eid]
        rows[eid] = {"shifts": n, "deductions": sums[eid], "salary": Decimal(n) * rate + sums[eid]}
    return rows

def shift_warnings(existing, candidate):
    """Return soft warnings for insufficient rest; candidate date is start date."""
    from datetime import timedelta
    people={candidate.cashier_id,candidate.hall_id}-{None}
    warnings=[]
    for old in existing:
        overlap=people & ({old.cashier_id,old.hall_id}-{None})
        if not overlap: continue
        same_day=old.date==candidate.date and old.shift_type!=candidate.shift_type
        night_to_day=(old.shift_type=='Ночь' and candidate.shift_type=='День' and candidate.date==old.date+timedelta(days=1))
        day_to_night=(candidate.shift_type=='Ночь' and old.shift_type=='День' and old.date==candidate.date+timedelta(days=1))
        if same_day: warnings.append({'employee_ids':sorted(overlap),'code':'same_date_day_night','message':'Сотрудник поставлен на День и Ночь одной даты'})
        elif night_to_day or day_to_night: warnings.append({'employee_ids':sorted(overlap),'code':'no_rest','message':'Между ночной сменой и дневной сменой следующей даты нет отдыха'})
    return warnings
