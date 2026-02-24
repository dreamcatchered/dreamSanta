import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-christmas-key-2025'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///santa_v6.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    SMS_API_KEY = os.environ.get("SMS_API_KEY", "YOUR_SMS_API_KEY_HERE")
    CRYPTO_BOT_TOKEN = os.environ.get("CRYPTO_BOT_TOKEN", "YOUR_CRYPTO_BOT_TOKEN_HERE")
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
    MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB - максимальный размер изображения после сжатия

