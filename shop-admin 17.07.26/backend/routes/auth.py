import os, secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession
from ..db import get_db
from ..models import LoginAttempt, Session, User
from ..schemas import LoginIn, OwnerSetupIn, PasswordChangeIn
from ..security import COOKIE, CSRF_COOKIE, digest, password_hash, current_user

router=APIRouter(prefix='/api/auth',tags=['auth'])
SECURE=os.getenv('COOKIE_SECURE','true').lower() in {'1','true','yes','on'}

def audit(db,user_id,action,ip):
    from ..models import AuditLog
    db.add(AuditLog(user_id=user_id,action=action,ip=ip))

@router.get('/setup-required')
def setup_required(db: DBSession=Depends(get_db)):
    return {'required': db.query(User).count()==0}

@router.post('/setup-owner')
def setup_owner(body: OwnerSetupIn,request: Request,response: Response,db: DBSession=Depends(get_db)):
    if db.query(User).count(): raise HTTPException(409,'Владелец уже создан')
    user=User(username=body.username.strip().lower(),password_hash=password_hash.hash(body.password),role='Владелец')
    db.add(user);db.flush();audit(db,user.id,'Создана учетная запись владельца',request.client.host);db.commit()
    csrf=secrets.token_urlsafe(32);token=secrets.token_urlsafe(48)
    db.add(Session(token_hash=digest(token),csrf_hash=digest(csrf),user_id=user.id,expires_at=datetime.now(timezone.utc)+timedelta(days=7)));db.commit()
    response.set_cookie(COOKIE,token,max_age=604800,httponly=True,secure=SECURE,samesite='lax',path='/')
    response.set_cookie(CSRF_COOKIE,csrf,max_age=604800,httponly=False,secure=SECURE,samesite='lax',path='/')
    return {'id':user.id,'username':user.username,'role':user.role,'csrf':csrf}

@router.post('/login')
def login(body: LoginIn,request: Request,response: Response,db: DBSession=Depends(get_db)):
    name=body.username.strip().lower();ip=request.client.host if request.client else 'unknown';now=datetime.now(timezone.utc);cut=now-timedelta(minutes=10)
    recent=db.query(LoginAttempt).filter(LoginAttempt.ip==ip,LoginAttempt.username==name,LoginAttempt.at>=cut,LoginAttempt.succeeded.is_(False)).count()
    blocked=db.query(LoginAttempt).filter(LoginAttempt.ip==ip,LoginAttempt.username==name,LoginAttempt.at>=now-timedelta(minutes=15),LoginAttempt.succeeded.is_(False)).count()>=5
    if blocked: raise HTTPException(429,'Слишком много попыток. Повторите через 15 минут.')
    user=db.query(User).filter(func.lower(User.username)==name).first()
    ok=bool(user and user.active and password_hash.verify(body.password,user.password_hash))
    db.add(LoginAttempt(ip=ip,username=name,succeeded=ok));db.commit()
    if not ok: raise HTTPException(401,'Неверный логин или пароль')
    csrf=secrets.token_urlsafe(32);token=secrets.token_urlsafe(48)
    db.add(Session(token_hash=digest(token),csrf_hash=digest(csrf),user_id=user.id,expires_at=now+timedelta(days=7)));audit(db,user.id,'Вход',ip);db.commit()
    response.set_cookie(COOKIE,token,max_age=604800,httponly=True,secure=SECURE,samesite='lax',path='/')
    response.set_cookie(CSRF_COOKIE,csrf,max_age=604800,httponly=False,secure=SECURE,samesite='lax',path='/')
    return {'id':user.id,'username':user.username,'role':user.role,'csrf':csrf}

@router.get('/me')
def me(user=Depends(current_user)):
    return {'id':user.id,'username':user.username,'role':user.role,'employee_id':user.employee_id,'employee_name':user.employee.name if user.employee_id else None,'must_change_password':user.must_change_password}

@router.post('/logout')
def logout(request:Request,response:Response,db:DBSession=Depends(get_db),user=Depends(current_user)):
    token=request.cookies.get(COOKIE);db.query(Session).filter_by(token_hash=digest(token or '')).delete();db.commit()
    response.delete_cookie(COOKIE,path='/');response.delete_cookie(CSRF_COOKIE,path='/');return {'ok':True}

@router.post('/change-password')
def change_password(body:PasswordChangeIn,request:Request,db:DBSession=Depends(get_db),user=Depends(current_user)):
    if not password_hash.verify(body.current_password,user.password_hash): raise HTTPException(400,'Текущий пароль указан неверно')
    user.password_hash=password_hash.hash(body.new_password);user.must_change_password=False;audit(db,user.id,'Изменен пароль',request.client.host if request.client else 'unknown');db.commit();return {'ok':True}
