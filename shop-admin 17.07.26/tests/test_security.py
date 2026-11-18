from datetime import date
from decimal import Decimal
from conftest import (login, csrf, OWNER_PASSWORD, ADMIN_PASSWORD, STAFF_PASSWORD, NEW_USER_PASSWORD, RESET_PASSWORD, UPDATED_PASSWORD, TEMP_PASSWORD, PERMANENT_PASSWORD, WRONG_PASSWORD)

def test_employee_forbidden_other_payroll_and_private_lists(client):
    login(client,'staff',STAFF_PASSWORD)
    assert client.get('/api/payroll',params={'start':'2026-11-16','end':'2026-11-22','employee_id':2}).status_code==403
    assert client.get('/api/shifts',params={'start':'2026-11-16','end':'2026-11-22'}).status_code==403
    assert client.get('/api/advances',params={'start':'2026-11-16','end':'2026-11-22'}).status_code==403

def test_admin_cannot_create_users(client):
    login(client,'admin',ADMIN_PASSWORD)
    response=client.post('/api/users',json={'username':'newstaff','password':NEW_USER_PASSWORD,'role':'Сотрудник','employee_id':1},headers=csrf(client))
    assert response.status_code==403

def test_failed_login_blocked_after_five_attempts(client):
    for n in range(5):
        response=client.post('/api/auth/login',json={'username':'owner','password':WRONG_PASSWORD})
        assert response.status_code==401, f'attempt {n+1}: {response.text}'
    assert client.post('/api/auth/login',json={'username':'owner','password':OWNER_PASSWORD}).status_code==429

def test_csrf_required_for_mutations(client):
    login(client,'admin',ADMIN_PASSWORD)
    response=client.post('/api/orders',json={'order_date':'2026-11-18','supplier':'Поставщик','items_text':'Товар','amount':'1200','status':'Новый'})
    assert response.status_code==403

def test_advance_negative_and_repayment_positive(client):
    login(client,'admin',ADMIN_PASSWORD)
    h=csrf(client)
    a=client.post('/api/advances',headers=h,json={'date':'2026-11-18','employee_id':1,'amount':'15000','comment':'Аванс'})
    assert a.status_code==200 and Decimal(a.json()['amount'])==Decimal('-15000')
    p=client.post('/api/repayments',headers=h,json={'date':'2026-11-18','employee_id':1,'amount':'5000','comment':'Погашение'})
    assert p.status_code==200 and Decimal(p.json()['amount'])==Decimal('5000')

def test_protected_routes_require_authentication(client):
    # Explicitly include CSRF so state-changing requests reach auth dependency.
    client.cookies.set('shop_csrf','test-csrf')
    h={'x-csrf-token':'test-csrf'}
    checks=[
      ('get','/api/users',None),('post','/api/users',{'username':'xuser','password':NEW_USER_PASSWORD,'role':'Сотрудник','employee_id':1}),
      ('patch','/api/users/1',{'active':False}),('get','/api/employees',None),('post','/api/employees',{'name':'X'}),
      ('get','/api/payroll',None),('get','/api/shifts',None),('post','/api/shifts',{'date':'2026-11-18','shift_type':'День','cashier_id':1}),('put','/api/shifts/1',{'date':'2026-11-18','shift_type':'День','cashier_id':1}),('delete','/api/shifts/1',None),
      ('get','/api/advances',None),('post','/api/advances',{'date':'2026-11-18','employee_id':1,'amount':1}),('post','/api/repayments',{'date':'2026-11-18','employee_id':1,'amount':1}),('delete','/api/advances/1',None),
      ('get','/api/orders',None),('post','/api/orders',{'order_date':'2026-11-18','supplier':'X','items_text':'X','amount':1}),('put','/api/orders/1',{'order_date':'2026-11-18','supplier':'X','items_text':'X','amount':1}),('delete','/api/orders/1',None),
      ('get','/api/settings/rate',None),('put','/api/settings/rate',{'rate':1}),('get','/api/backup',None),('get','/api/audit',None),('post','/api/auth/logout',None),('post','/api/auth/change-password',{'current_password':WRONG_PASSWORD,'new_password':NEW_USER_PASSWORD})]
    for method,path,payload in checks:
        kwargs={'headers':h}
        if payload is not None:kwargs['json']=payload
        response=getattr(client,method)(path,**kwargs)
        assert response.status_code==401, f'{method.upper()} {path}: expected 401, got {response.status_code}: {response.text}'

def test_user_management_and_password_change(client):
    login(client,'owner',OWNER_PASSWORD);h=csrf(client)
    created=client.post('/api/users',headers=h,json={'username':'new-user','password':NEW_USER_PASSWORD,'role':'Сотрудник','employee_id':1})
    assert created.status_code==200
    uid=created.json()['id']
    assert client.patch(f'/api/users/{uid}',headers=h,json={'active':False}).status_code==200
    assert client.patch(f'/api/users/{uid}',headers=h,json={'active':True,'password':RESET_PASSWORD}).status_code==200
    login(client,'admin',ADMIN_PASSWORD)
    change=client.post('/api/auth/change-password',headers=csrf(client),json={'current_password':ADMIN_PASSWORD,'new_password':UPDATED_PASSWORD})
    assert change.status_code==200
    client.post('/api/auth/logout',headers=csrf(client))
    assert login(client,'admin',UPDATED_PASSWORD).status_code==200

def test_role_matrix_for_edit_delete_shifts_orders_advances(client):
    login(client,'owner',OWNER_PASSWORD);h=csrf(client)
    shift=client.post('/api/shifts',headers=h,json={'date':'2026-11-18','shift_type':'День','cashier_id':1,'hall_id':2}).json()['id']
    order=client.post('/api/orders',headers=h,json={'order_date':'2026-11-18','supplier':'S','items_text':'I','amount':10,'status':'Новый'}).json()['id']
    advance=client.post('/api/advances',headers=h,json={'date':'2026-11-18','employee_id':1,'amount':10}).json()['id']
    login(client,'admin',ADMIN_PASSWORD);h=csrf(client)
    assert client.put(f'/api/shifts/{shift}',headers=h,json={'date':'2026-11-18','shift_type':'Ночь','cashier_id':1,'hall_id':2}).status_code==200
    assert client.put(f'/api/orders/{order}',headers=h,json={'order_date':'2026-11-18','supplier':'S2','items_text':'I','amount':11,'status':'Заказан'}).status_code==200
    assert client.delete(f'/api/shifts/{shift}',headers=h).status_code==403
    assert client.delete(f'/api/orders/{order}',headers=h).status_code==403
    assert client.delete(f'/api/advances/{advance}',headers=h).status_code==403
    login(client,'staff',STAFF_PASSWORD);h=csrf(client)
    assert client.put(f'/api/shifts/{shift}',headers=h,json={'date':'2026-11-18','shift_type':'День','cashier_id':1}).status_code==403
    assert client.put(f'/api/orders/{order}',headers=h,json={'order_date':'2026-11-18','supplier':'S','items_text':'I','amount':1}).status_code==403
    assert client.delete(f'/api/advances/{advance}',headers=h).status_code==403
    login(client,'owner',OWNER_PASSWORD);h=csrf(client)
    assert client.delete(f'/api/shifts/{shift}',headers=h).status_code==200
    assert client.delete(f'/api/orders/{order}',headers=h).status_code==200
    assert client.delete(f'/api/advances/{advance}',headers=h).status_code==200

def test_mutations_are_audited(client):
    login(client,'owner',OWNER_PASSWORD);h=csrf(client)
    client.post('/api/employees',headers=h,json={'name':'New employee'})
    client.put('/api/settings/rate',headers=h,json={'rate':12000})
    client.post('/api/users',headers=h,json={'username':'logged-user','password':NEW_USER_PASSWORD,'role':'Администратор'})
    client.post('/api/shifts',headers=h,json={'date':'2026-11-18','shift_type':'День','cashier_id':1})
    client.post('/api/orders',headers=h,json={'order_date':'2026-11-18','supplier':'S','items_text':'I','amount':1})
    client.post('/api/advances',headers=h,json={'date':'2026-11-18','employee_id':1,'amount':1})
    client.post('/api/repayments',headers=h,json={'date':'2026-11-18','employee_id':1,'amount':1})
    actions=[x['action'] for x in client.get('/api/audit').json()]
    assert len(actions)>=7
    assert any('сотрудник' in x.lower() for x in actions)
    assert any('ставка' in x.lower() for x in actions)
    assert any('погашен' in x.lower() for x in actions)

def test_backup_is_nonempty_and_restores_demo_payroll(client,tmp_path):
    from backend.db import SessionLocal
    from backend.models import Employee,Shift,Setting
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session as DBSession
    from backend.services.payroll import calculate_payroll
    from decimal import Decimal
    from datetime import date
    names=['Азамат','Айбек','Айгерим','Аяу','Балу','Венера','Жанай','Жанель','Жулдыз','Инжу']
    pairs=[('Жулдыз','Балу'),('Айгерим','Венера'),('Жулдыз','Инжу'),('Балу','Айбек'),('Аяу','Инжу'),('Балу','Венера'),('Аяу','Инжу'),('Жулдыз','Азамат'),('Жанай','Жанель'),('Жулдыз','Балу'),('Жанай','Жанель'),('Аяу','Инжу'),('Балу','Азамат'),('Инжу','Балу')]
    with SessionLocal() as db:
        emps={n:Employee(name=n) for n in names};db.add_all(emps.values());db.flush()
        db.add(Setting(key='rate_per_shift',value='10000'))
        for i,(cash,hall) in enumerate(pairs):db.add(Shift(date=date(2026,11,16+i//2),shift_type='День' if i%2==0 else 'Ночь',cashier_id=emps[cash].id,hall_id=emps[hall].id))
        db.commit()
    login(client,'owner',OWNER_PASSWORD)
    response=client.get('/api/backup')
    assert response.status_code==200 and len(response.content)>100
    target=tmp_path/'restored.db';target.write_bytes(response.content)
    engine=create_engine(f'sqlite:///{target}')
    with DBSession(engine) as db:
        restored=calculate_payroll(db,date(2026,11,16),date(2026,11,22),Decimal(10000))
        assert sum(r['shifts'] for r in restored.values())==28
        assert sum(r['salary'] for r in restored.values())==Decimal(280000)

def test_temporary_password_forces_change_before_business_access(client):
    login(client,'owner',OWNER_PASSWORD);h=csrf(client)
    made=client.post('/api/users',headers=h,json={'username':'temp-user','password':TEMP_PASSWORD,'role':'Администратор'})
    assert made.status_code==200
    client.post('/api/auth/logout',headers=csrf(client))
    assert login(client,'temp-user',TEMP_PASSWORD).status_code==200
    assert client.get('/api/orders').status_code==403
    changed=client.post('/api/auth/change-password',headers=csrf(client),json={'current_password':TEMP_PASSWORD,'new_password':PERMANENT_PASSWORD})
    assert changed.status_code==200
    assert client.get('/api/orders').status_code==200

def test_disabled_user_cannot_login(client):
    login(client,'owner',OWNER_PASSWORD)
    assert client.patch('/api/users/3',headers=csrf(client),json={'active':False}).status_code==200
    client.post('/api/auth/logout',headers=csrf(client))
    assert login(client,'staff',STAFF_PASSWORD).status_code==401

def test_logout_invalidates_session_and_account_switch_has_no_previous_data(client):
    login(client,'owner',OWNER_PASSWORD)
    assert client.get('/api/users').status_code==200
    assert client.post('/api/auth/logout',headers=csrf(client)).status_code==200
    assert client.get('/api/users').status_code==401
    login(client,'staff',STAFF_PASSWORD)
    assert client.get('/api/users').status_code==403
    assert client.get('/api/payroll',params={'start':'2026-11-16','end':'2026-11-22'}).json()['employee_id']==1

def test_employee_only_receives_own_payroll_after_login(client):
    login(client,'staff',STAFF_PASSWORD)
    r=client.get('/api/payroll',params={'start':'2026-11-16','end':'2026-11-22'})
    assert r.status_code==200 and r.json()['employee_id']==1
    assert client.get('/api/payroll',params={'start':'2026-11-16','end':'2026-11-22','employee_id':2}).status_code==403
