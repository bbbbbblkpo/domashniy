import os, logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from .db import Base, engine
from .routes.auth import router as auth_router
from .routes.api import router as api_router
from .security import enforce_csrf
from .models import *

logging.basicConfig(level=logging.INFO)
if os.getenv('APP_ENV','production')!='development' and not os.getenv('SECRET_KEY'):
    raise RuntimeError('Не задан SECRET_KEY: установите секрет через переменные окружения')
app=FastAPI(title='Смены',debug=False,docs_url=None,redoc_url=None,openapi_url=None)
Base.metadata.create_all(bind=engine)
app.include_router(auth_router);app.include_router(api_router)
@app.middleware('http')
async def protections(request:Request,call_next):
    if os.getenv('APP_ENV','production')!='development' and request.url.scheme!='https' and request.headers.get('x-forwarded-proto')!='https':
        return RedirectResponse(str(request.url.replace(scheme='https')),status_code=308)
    if request.method in {'POST','PUT','PATCH','DELETE'} and request.url.path not in {'/api/auth/login','/api/auth/setup-owner'}:
        try: enforce_csrf(request)
        except HTTPException as exc: return JSONResponse({'detail':exc.detail},status_code=exc.status_code)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff';response.headers['X-Frame-Options']='DENY';response.headers['Referrer-Policy']='strict-origin-when-cross-origin'
    response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
    response.headers['X-Robots-Tag']='noindex, nofollow, noarchive'
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control']='no-store, max-age=0'
    if request.url.scheme=='https' or request.headers.get('x-forwarded-proto')=='https':response.headers['Strict-Transport-Security']='max-age=31536000; includeSubDomains'
    return response
@app.get('/health')
def health():return {'status':'ok'}
@app.exception_handler(404)
async def not_found(request,exc):return JSONResponse({'detail':'Страница не найдена'},status_code=404)
@app.exception_handler(500)
async def server_error(request,exc):return JSONResponse({'detail':'Внутренняя ошибка сервера'},status_code=500)

@app.get('/')
def index(): return FileResponse('index.html')
@app.get('/app.js')
def frontend_js(): return FileResponse('app.js',media_type='application/javascript')
@app.get('/styles.css')
def frontend_css(): return FileResponse('styles.css',media_type='text/css')
@app.get('/privacy')
def privacy(): return FileResponse('privacy.html',media_type='text/html; charset=utf-8')
@app.get('/terms')
def terms(): return FileResponse('terms.html',media_type='text/html; charset=utf-8')
@app.get('/robots.txt')
def robots():
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse('User-agent: *\nDisallow: /\n')
