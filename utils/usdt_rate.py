# -*- coding: utf-8 -*-
"""
Утилита для получения курса USDT/RUB онлайн
"""
import requests
import time
from functools import lru_cache

# Кэш для курса (обновляется каждые 5 минут)
_rate_cache = {'rate': None, 'timestamp': 0}
CACHE_TTL = 300  # 5 минут

@lru_cache(maxsize=1)
def get_usdt_rub_rate():
    """
    Получает курс USDT/RUB онлайн через CoinGecko API
    Возвращает курс или None в случае ошибки
    """
    try:
        # Пробуем CoinGecko API (бесплатный, без API ключа)
        # Tether (USDT) id: tether
        # RUB - российский рубль
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            'ids': 'tether',
            'vs_currencies': 'rub',
            'include_24hr_change': 'false'
        }
        
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            rate = data.get('tether', {}).get('rub')
            if rate:
                return float(rate)
    except Exception as e:
        print(f"⚠️ Ошибка получения курса из CoinGecko: {e}")
    
    try:
        # Запасной вариант: Binance API
        url = "https://api.binance.com/api/v3/ticker/price"
        params = {'symbol': 'USDTRUB'}
        
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            rate = data.get('price')
            if rate:
                return float(rate)
    except Exception as e:
        print(f"⚠️ Ошибка получения курса из Binance: {e}")
    
    # Если все API недоступны, возвращаем None
    return None

def get_cached_usdt_rate():
    """
    Получает курс USDT/RUB с кэшированием (5 минут)
    Если курс получить не удалось, возвращает значение по умолчанию (100)
    """
    global _rate_cache
    current_time = time.time()
    
    # Проверяем, нужно ли обновить кэш
    if (_rate_cache['rate'] is None or 
        current_time - _rate_cache['timestamp'] > CACHE_TTL):
        
        rate = get_usdt_rub_rate()
        if rate:
            _rate_cache['rate'] = rate
            _rate_cache['timestamp'] = current_time
        elif _rate_cache['rate'] is None:
            # Если кэш пустой и не удалось получить курс, используем значение по умолчанию
            _rate_cache['rate'] = 100.0
            _rate_cache['timestamp'] = current_time
    
    return _rate_cache['rate']



