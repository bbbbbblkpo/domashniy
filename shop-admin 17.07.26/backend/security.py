import hashlib, hmac, os, secrets
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, Request
from pwdlib import PasswordHash
from sqlalchemy.orm import Session as DBSession
from .db import get_db
from .models import LoginAttempt, Session, User

password_hash = PasswordHash.recommended()
COOKIE = 'shop_session'
CSRF_COOKIE = 'shop_csrf'

def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()

def current_user(request: Request, db: DBSession = Depends(get_db)) -> User:
    token = request.cookies.get(COOKIE)
    session = db.query(Session).filter_by(token_hash=digest(token or '')).first()
    if not session or session.expires_at.replace(tzinfo=session.expires_at.tzinfo or timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(401, 'Требуется вход')
    user = db.get(User, session.user_id)
    if not user or not user.active:
        raise HTTPException(401, 'Учетная запись отключена')
    if user.must_change_password and request.url.path not in {'/api/auth/me','/api/auth/change-password','/api/auth/logout'}:
        raise HTTPException(403, 'Сначала смените временный пароль')
    return user

def require_roles(*roles):
    def dependency(user: User = Depends(current_user)):
        if user.role not in roles:
            raise HTTPException(403, 'Недостаточно прав')
        return user
    return dependency

def enforce_csrf(request: Request):
    if request.method in {'POST','PUT','PATCH','DELETE'}:
        cookie = request.cookies.get(CSRF_COOKIE, '')
        header = request.headers.get('x-csrf-token', '')
        if not cookie or not hmac.compare_digest(cookie, header):
            raise HTTPException(403, 'Ошибка CSRF-проверки')
