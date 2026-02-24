#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Production entry point for Santa application
"""
import os
from app import create_app

if __name__ == '__main__':
    app = create_app()
    
    # Получаем порт из переменной окружения, по умолчанию 5029
    port = int(os.environ.get('PORT', '5029'))
    host = os.environ.get('HOST', '127.0.0.1')
    debug = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 'yes')
    
    print(f"🚀 Запуск Santa приложения на {host}:{port}")
    print(f"🌐 Приложение будет доступно на https://santa.dreampartners.online")
    
    app.run(host=host, port=port, debug=debug)

