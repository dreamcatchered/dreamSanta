# -*- coding: utf-8 -*-
"""
Утилиты для работы с московским временем
"""
from datetime import datetime
import pytz

# Московская временная зона
MSK_TZ = pytz.timezone('Europe/Moscow')

def now_msk():
    """Возвращает текущее время в МСК"""
    return datetime.now(MSK_TZ)

def utc_to_msk(utc_dt):
    """Конвертирует UTC время в МСК"""
    if utc_dt.tzinfo is None:
        # Если время без tzinfo, считаем его UTC
        utc_dt = pytz.utc.localize(utc_dt)
    return utc_dt.astimezone(MSK_TZ)

def msk_to_utc(msk_dt):
    """Конвертирует МСК время в UTC"""
    if msk_dt.tzinfo is None:
        # Если время без tzinfo, считаем его МСК
        msk_dt = MSK_TZ.localize(msk_dt)
    return msk_dt.astimezone(pytz.utc).replace(tzinfo=None)  # Убираем tzinfo для совместимости с БД



