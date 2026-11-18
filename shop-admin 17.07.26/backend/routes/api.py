from datetime import date, timedelta, datetime, timezone
from decimal import Decimal
import os, shutil, tempfile, subprocess
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.engine import make_url
from ..db import DEMO_MODE, get_db
from ..models import Advance, AuditLog, Employee, Order, Setting, Shift, User
from ..schemas import AdvanceIn, EmployeeIn, OrderIn, RateIn, RepaymentIn, ShiftIn, UserCreateIn
from ..security import password_hash, require_roles
from ..services.payroll import calculate_payroll, shift_warnings

router=APIRouter(prefix='/api',tags=['application'])
@router.get('/config')
def public_config():
    return {'demo_mode':DEMO_MODE}

@router.get('/period/current-week')
def current_week():
    from ..services.timezone import week_bounds
    a,b=week_bounds();return {'start':a.isoformat(),'end':b.isoformat()}
def log(db,user,req,what):
    db.add(AuditLog(user_id=user.id,action=what,ip=req.client.host if req.client else 'unknown'))
def employee_scope(user, employee_id):
    if user.role=='Сотрудник' and user.employee_id!=employee_id: raise HTTPException(403,'Доступ только к своим данным')
def require_employee_data(user):
    if user.role not in {'Владелец','Администратор'}: raise HTTPException(403,'Недостаточно прав')

@router.get('/users')
def users(db:DBSession=Depends(get_db),user=Depends(require_roles('Владелец'))):
    return [{'id':u.id,'username':u.username,'role':u.role,'employee_id':u.employee_id,'active':u.active} for u in db.query(User).all()]
@router.post('/users')
def create_user(body:UserCreateIn,request:Request,db:DBSession=Depends(get_db),owner=Depends(require_roles('Владелец'))):
    name=body.username.strip().lower()
    if db.query(User).filter_by(username=name).first():raise HTTPException(409,'Логин уже используется')
    if body.role=='Сотрудник' and (not body.employee_id or not db.get(Employee,body.employee_id)):raise HTTPException(422,'Выберите сотрудника из списка')
    u=User(username=name,password_hash=password_hash.hash(body.password),role=body.role,employee_id=body.employee_id,must_change_password=True);db.add(u);db.flush();log(db,owner,request,f'Создан пользователь {name}');db.commit();return {'id':u.id}
@router.patch('/users/{user_id}')
def update_user(user_id:int,request:Request,body:dict,db:DBSession=Depends(get_db),owner=Depends(require_roles('Владелец'))):
    u=db.get(User,user_id)
    if not u:raise HTTPException(404,'Пользователь не найден')
    if 'active' in body:u.active=bool(body['active'])
    if 'password' in body:
        if len(body['password'])<10:raise HTTPException(422,'Пароль должен содержать не менее 10 символов')
        u.password_hash=password_hash.hash(body['password']);u.must_change_password=True
    if 'employee_id' in body:u.employee_id=body['employee_id']
    log(db,owner,request,f'Изменен пользователь {u.username}');db.commit();return {'ok':True}
@router.get('/employees')
def employees(db:DBSession=Depends(get_db),user=Depends(require_roles('Владелец','Администратор'))):
    return [{'id':e.id,'name':e.name,'active':e.active} for e in db.query(Employee).filter_by(active=True).all()]
@router.post('/employees')
def create_employee(body:EmployeeIn,request:Request,db:DBSession=Depends(get_db),owner=Depends(require_roles('Владелец'))):
    name=' '.join(body.name.split());existing=db.query(Employee).all()
    if any(' '.join(e.name.split()).casefold()==name.casefold() for e in existing):raise HTTPException(409,'Сотрудник с таким именем уже есть')
    e=Employee(name=name);db.add(e);db.flush();log(db,owner,request,f'Добавлен сотрудник {name}');db.commit();return {'id':e.id}
@router.get('/payroll')
def payroll(start:date,end:date,employee_id:int|None=None,db:DBSession=Depends(get_db),user=Depends(require_roles('Владелец','Администратор','Сотрудник'))):
    if end<start:raise HTTPException(422,'Конец периода раньше начала')
    if user.role=='Сотрудник':
        if user.employee_id is None:raise HTTPException(403,'Профиль не привязан к сотруднику')
        if employee_id is not None and employee_id!=user.employee_id:raise HTTPException(403,'Доступ только к личному расчету')
        employee_id=user.employee_id
    setting=db.query(Setting).filter_by(key='rate_per_shift').first();rate=Decimal(setting.value if setting else '10000')
    rows=calculate_payroll(db,start,end,rate)
    if employee_id is not None:return {'employee_id':employee_id,**{k:str(v) for k,v in rows.get(employee_id,{'shifts':0,'deductions':Decimal(0),'salary':Decimal(0)}).items()}}
    return {str(eid):{k:str(v) for k,v in row.items()} for eid,row in rows.items()}
@router.get('/shifts')
def shifts(start:date,end:date,db:DBSession=Depends(get_db),user=Depends(require_roles('Владелец','Администратор'))):
    return [{'id':s.id,'date':s.date.isoformat(),'shift_type':s.shift_type,'cashier_id':s.cashier_id,'hall_id':s.hall_id} for s in db.query(Shift).filter(Shift.date.between(start,end)).all()]
def shift_warnings_for(db, candidate):
    existing=db.query(Shift).filter(Shift.date.between(candidate.date-timedelta(days=1),candidate.date+timedelta(days=1))).all()
    return shift_warnings(existing,candidate)
def validate_staff(db,body):
    for eid in {body.cashier_id,body.hall_id}-{None}:
        e=db.get(Employee,eid)
        if not e or not e.active:raise HTTPException(422,'Выберите активного сотрудника')
@router.post('/shifts')
def create_shift(body:ShiftIn,request:Request,db:DBSession=Depends(get_db),user=Depends(require_roles('Владелец','Администратор'))):
    validate_staff(db,body);s=Shift(date=body.date,shift_type=body.shift_type,cashier_id=body.cashier_id,hall_id=body.hall_id);warnings=shift_warnings_for(db,s)
    if warnings and not body.confirm_warnings:return {'warning':True,'warnings':warnings,'message':'Обнаружен конфликт. Повторите запрос с confirm_warnings=true для сохранения.'}
    db.add(s);db.flush();log(db,user,request,f'Создана смена {s.id}');db.commit();return {'id':s.id,'warnings':warnings}
@router.put('/shifts/{shift_id}')
def edit_shift(shift_id:int,body:ShiftIn,request:Request,db:DBSession=Depends(get_db),user=Depends(require_roles('Владелец','Администратор'))):
    s=db.get(Shift,shift_id)
    if not s:raise HTTPException(404,'Смена не найдена')
    validate_staff(db,body);candidate=Shift(date=body.date,shift_type=body.shift_type,cashier_id=body.cashier_id,hall_id=body.hall_id);existing=[x for x in db.query(Shift).filter(Shift.date.between(body.date-timedelta(days=1),body.date+timedelta(days=1))).all() if x.id!=shift_id];warnings=shift_warnings(existing,candidate)
    if warnings and not body.confirm_warnings:return {'warning':True,'warnings':warnings,'message':'Обнаружен конфликт. Повторите запрос с confirm_warnings=true для сохранения.'}
    for k,v in body.model_dump(exclude={'confirm_warnings'}).items():setattr(s,k,v)
    log(db,user,request,f'Изменена смена {s.id}');db.commit();return {'ok':True,'warnings':warnings}
@router.delete('/shifts/{shift_id}')
def delete_shift(shift_id:int,request:Request,db:DBSession=Depends(get_db),user=Depends(require_roles('Владелец'))):
    s=db.get(Shift,shift_id)
    if not s:raise HTTPException(404,'Смена не найдена')
    db.delete(s);log(db,user,request,f'Удалена смена {shift_id}');db.commit();return {'ok':True}
@router.get('/advances')
def advances(start:date,end:date,employee_id:int|None=None,db:DBSession=Depends(get_db),user=Depends(require_roles('Владелец','Администратор'))):
    q=db.query(Advance).filter(Advance.date.between(start,end))
    if employee_id is not None:q=q.filter(Advance.employee_id==employee_id)
    return [{'id':x.id,'date':x.date.isoformat(),'employee_id':x.employee_id,'amount':str(x.amount),'comment':x.comment} for x in q.all()]
@router.post('/advances')
def create_advance(body:AdvanceIn,request:Request,db:DBSession=Depends(get_db),user=Depends(require_roles('Владелец','Администратор'))):
    if not db.get(Employee,body.employee_id):raise HTTPException(422,'Сотрудник не найден')
    item=Advance(date=body.date,employee_id=body.employee_id,amount=-abs(body.amount),comment=body.comment);db.add(item);db.flush();log(db,user,request,f'Создан долг/аванс {item.id}');db.commit();return {'id':item.id,'amount':str(item.amount)}
@router.post('/repayments')
def repay(body:RepaymentIn,request:Request,db:DBSession=Depends(get_db),user=Depends(require_roles('Владелец','Администратор'))):
    if not db.get(Employee,body.employee_id):raise HTTPException(422,'Сотрудник не найден')
    item=Advance(date=body.date,employee_id=body.employee_id,amount=abs(body.amount),comment=body.comment or 'Погашение');db.add(item);db.flush();log(db,user,request,f'Погашен долг {item.id}');db.commit();return {'id':item.id,'amount':str(item.amount)}
@router.delete('/advances/{advance_id}')
def delete_advance(advance_id:int,request:Request,db:DBSession=Depends(get_db),user=Depends(require_roles('Владелец'))):
    x=db.get(Advance,advance_id)
    if not x:raise HTTPException(404,'Запись не найдена')
    db.delete(x);log(db,user,request,f'Удалена запись аванса {advance_id}');db.commit();return {'ok':True}
@router.get('/orders')
def orders(db:DBSession=Depends(get_db),user=Depends(require_roles('Владелец','Администратор'))):
    return [{'id':o.id,'order_date':o.order_date.isoformat(),'supplier':o.supplier,'items_text':o.items_text,'amount':str(o.amount),'delivery_date':o.delivery_date.isoformat() if o.delivery_date else None,'status':o.status,'comment':o.comment} for o in db.query(Order).order_by(Order.order_date.desc()).all()]
@router.post('/orders')
def create_order(body:OrderIn,request:Request,db:DBSession=Depends(get_db),user=Depends(require_roles('Владелец','Администратор'))):
    if body.status not in {'Новый','Заказан','Доставлен','Оплачен','Отменён'}:raise HTTPException(422,'Некорректный статус')
    item=Order(**body.model_dump(),created_by=user.id);db.add(item);db.flush();log(db,user,request,f'Создан заказ {item.id}');db.commit();return {'id':item.id}
@router.put('/orders/{order_id}')
def edit_order(order_id:int,body:OrderIn,request:Request,db:DBSession=Depends(get_db),user=Depends(require_roles('Владелец','Администратор'))):
    o=db.get(Order,order_id)
    if not o:raise HTTPException(404,'Заказ не найден')
    for k,v in body.model_dump().items():setattr(o,k,v)
    log(db,user,request,f'Изменен заказ {o.id}');db.commit();return {'ok':True}
@router.delete('/orders/{order_id}')
def delete_order(order_id:int,request:Request,db:DBSession=Depends(get_db),user=Depends(require_roles('Владелец'))):
    o=db.get(Order,order_id)
    if not o:raise HTTPException(404,'Заказ не найден')
    db.delete(o);log(db,user,request,f'Удален заказ {order_id}');db.commit();return {'ok':True}
@router.get('/settings/rate')
def get_rate(db:DBSession=Depends(get_db),user=Depends(require_roles('Владелец','Администратор'))):
    row=db.query(Setting).filter_by(key='rate_per_shift').first();return {'rate':row.value if row else '10000'}
@router.put('/settings/rate')
def set_rate(body:RateIn,request:Request,db:DBSession=Depends(get_db),owner=Depends(require_roles('Владелец'))):
    row=db.query(Setting).filter_by(key='rate_per_shift').first()
    if row:row.value=str(body.rate)
    else:db.add(Setting(key='rate_per_shift',value=str(body.rate)))
    log(db,owner,request,'Изменена ставка смены');db.commit();return {'rate':str(body.rate)}
@router.get('/backup')
def backup(db:DBSession=Depends(get_db),owner=Depends(require_roles('Владелец'))):
    if DEMO_MODE: raise HTTPException(403,'Резервное копирование отключено в демо-режиме')
    url=os.getenv('DATABASE_URL','sqlite:///./data.db')
    if url.startswith('sqlite'):
        path=url.replace('sqlite:///','',1)
        if not os.path.isfile(path):raise HTTPException(404,'Файл базы не найден')
        return FileResponse(path,filename='shifts-backup.db',media_type='application/octet-stream')
    fd,path=tempfile.mkstemp(suffix='.sql');os.close(fd)
    try:
        # SQLAlchemy driver suffixes (for example +psycopg) are not accepted
        # by pg_dump's PostgreSQL URI parser.
        pg_url=make_url(url).set(drivername='postgresql').render_as_string(hide_password=False)
        subprocess.run(['pg_dump',pg_url,'-f',path],check=True,capture_output=True,text=True)
    except Exception as exc:
        if os.path.exists(path):os.unlink(path)
        raise HTTPException(500,'Не удалось создать резервную копию') from exc
    return FileResponse(path,filename='shifts-backup.sql',media_type='application/sql',background=BackgroundTask(os.unlink,path))
@router.get('/audit')
def audit(db:DBSession=Depends(get_db),user=Depends(require_roles('Владелец'))):
    return [{'user_id':x.user_id,'at':x.at.isoformat(),'action':x.action,'ip':x.ip} for x in db.query(AuditLog).order_by(AuditLog.at.desc()).limit(1000)]

@router.post('/demo/reset')
def reset_demo(request:Request,db:DBSession=Depends(get_db),owner=Depends(require_roles('Владелец'))):
    if not DEMO_MODE: raise HTTPException(404,'Демо-режим отключен')
    from ..demo_seed import reset_demo_data
    reset_demo_data(db)
    log(db,owner,request,'Сброшены демо-данные')
    db.commit()
    return {'ok':True,'message':'Демо-данные сброшены'}
