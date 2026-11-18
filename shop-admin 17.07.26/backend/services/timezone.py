from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo
SHOP_TZ=ZoneInfo('Asia/Almaty')
def shop_today(now=None): return (now or datetime.now(SHOP_TZ)).astimezone(SHOP_TZ).date()
def week_bounds(now=None):
    day=shop_today(now);start=day-timedelta(days=day.weekday());return start,start+timedelta(days=6)
