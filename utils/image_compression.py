# -*- coding: utf-8 -*-
"""
Утилита для сжатия изображений
"""
import os
from io import BytesIO
from PIL import Image
from config import Config

def compress_image(file, max_size_mb=5, quality=85):
    """
    Сжимает изображение до указанного размера
    
    Args:
        file: файловый объект (из Flask request.files)
        max_size_mb: максимальный размер в МБ
        quality: качество JPEG (1-100)
    
    Returns:
        BytesIO объект со сжатым изображением или None при ошибке
    """
    try:
        # Сохраняем текущую позицию
        original_position = file.tell()
        file.seek(0)
        
        # Читаем исходное изображение
        img = Image.open(file.stream)
        
        # Возвращаем позицию обратно
        file.seek(original_position)
        
        # Конвертируем RGBA в RGB для JPEG
        if img.mode in ('RGBA', 'LA', 'P'):
            # Создаем белый фон
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            rgb_img.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = rgb_img
        
        max_size_bytes = max_size_mb * 1024 * 1024
        
        # Пробуем сохранить с текущими параметрами
        output = BytesIO()
        img_format = img.format or 'JPEG'
        save_format = 'JPEG' if img_format in ('JPEG', 'JPG') else 'PNG'
        
        # Если формат не JPEG, конвертируем
        if save_format == 'JPEG' and img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Пробуем сохранить с уменьшением качества, если нужно
        for q in range(quality, 20, -10):
            output.seek(0)
            output.truncate(0)
            
            if save_format == 'JPEG':
                img.save(output, format='JPEG', quality=q, optimize=True)
            else:
                img.save(output, format='PNG', optimize=True)
            
            if output.tell() <= max_size_bytes:
                break
            
            # Если файл все еще большой, уменьшаем размер
            if output.tell() > max_size_bytes:
                width, height = img.size
                scale_factor = (max_size_bytes / output.tell()) ** 0.5
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        output.seek(0)
        return output
        
    except Exception as e:
        print(f"⚠️ Ошибка сжатия изображения: {e}")
        return None

def should_compress(file):
    """
    Проверяет, нужно ли сжимать файл
    """
    if not file:
        return False
    
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    max_size = Config.MAX_IMAGE_SIZE if hasattr(Config, 'MAX_IMAGE_SIZE') else 5 * 1024 * 1024
    return file_size > max_size

