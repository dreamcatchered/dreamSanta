# -*- coding: utf-8 -*-
"""
SEO утилиты для генерации мета-тегов и структурированных данных
"""
from flask import request
from models import Dream, User


class SEOGenerator:
    """Генератор SEO мета-тегов и структурированных данных"""
    
    BASE_URL = "https://santa.dreampartners.online"
    SITE_NAME = "Dream Santa - Маркет Желаний"
    DEFAULT_DESCRIPTION = "Платформа для исполнения мечтаний. Загадай мечту или помоги исполнить чужую."
    DEFAULT_IMAGE = "https://api.dreampartners.online/icons/santa/og-image.png"
    
    @staticmethod
    def generate_dream_meta(dream):
        """Генерирует SEO мета-данные для страницы мечты"""
        if not dream:
            return {}
        
        title = f"{dream.title} - {dream.price:.0f}₽ | Маркет Желаний"
        description = f"Исполним мечту: {dream.title}. {dream.description or 'Помогите исполнить эту мечту!'}"
        
        # Используем изображение мечты или дефолтное
        image_url = dream.image_url if dream.image_url and not dream.image_url.startswith('http') else dream.image_url
        if not image_url or not image_url.startswith('http'):
            image_url = SEOGenerator.DEFAULT_IMAGE
        else:
            image_url = request.host_url.rstrip('/') + image_url if image_url.startswith('/') else image_url
        
        return {
            'title': title,
            'description': description[:160],  # Ограничение для meta description
            'image': image_url,
            'type': 'article',
            'schema_type': 'Product',
            'canonical': f"{SEOGenerator.BASE_URL}/app#dream={dream.id}"
        }
    
    @staticmethod
    def generate_user_meta(user):
        """Генерирует SEO мета-данные для публичного профиля пользователя"""
        if not user:
            return {}
        
        role_text = {
            'santa': '🎅 Санта',
            'dreamer': '✨ Мечтатель',
            'admin': '⭐ Администратор'
        }.get(user.role, 'Пользователь')
        
        title = f"{user.name} (@{user.username}) - {role_text} | Маркет Желаний"
        description = f"Профиль {role_text.lower()}а {user.name}. {user.bio or 'Присоединяйся к платформе исполнения мечтаний!'}"
        
        # Аватар пользователя
        image_url = user.avatar_url if user.avatar_url and user.avatar_url.startswith('http') else None
        if not image_url:
            image_url = f"https://api.dicebear.com/7.x/avataaars/svg?seed={user.avatar_seed or 'Santa'}"
        
        return {
            'title': title,
            'description': description[:160],
            'image': image_url,
            'type': 'profile',
            'schema_type': 'ProfilePage',
            'canonical': f"{SEOGenerator.BASE_URL}/@{user.username}"
        }
    
    @staticmethod
    def generate_dream_schema(dream):
        """Генерирует структурированные данные Schema.org для мечты"""
        if not dream:
            return {}
        
        schema = {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": dream.title,
            "description": dream.description or "",
            "category": dream.category,
            "offers": {
                "@type": "Offer",
                "price": str(dream.price),
                "priceCurrency": "RUB",
                "availability": "https://schema.org/InStock" if dream.status == 'approved' else "https://schema.org/OutOfStock"
            },
            "image": dream.image_url if dream.image_url else SEOGenerator.DEFAULT_IMAGE
        }
        
        if dream.author:
            schema["brand"] = {
                "@type": "Person",
                "name": dream.author.name,
                "url": f"{SEOGenerator.BASE_URL}/@{dream.author.username}"
            }
        
        return schema
    
    @staticmethod
    def generate_user_schema(user):
        """Генерирует структурированные данные Schema.org для пользователя"""
        if not user:
            return {}
        
        schema = {
            "@context": "https://schema.org",
            "@type": "Person",
            "name": user.name,
            "url": f"{SEOGenerator.BASE_URL}/@{user.username}",
            "image": user.avatar_url if user.avatar_url else f"https://api.dicebear.com/7.x/avataaars/svg?seed={user.avatar_seed or 'Santa'}",
            "description": user.bio or ""
        }
        
        if user.telegram:
            schema["sameAs"] = [f"https://t.me/{user.telegram.replace('@', '')}"]
        
        return schema
    
    @staticmethod
    def generate_organization_schema():
        """Генерирует структурированные данные для организации"""
        return {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": SEOGenerator.SITE_NAME,
            "url": SEOGenerator.BASE_URL,
            "logo": "https://api.dreampartners.online/icons/santa/logo.svg",
            "description": SEOGenerator.DEFAULT_DESCRIPTION,
            "sameAs": []
        }
    
    @staticmethod
    def generate_breadcrumb_schema(items):
        """Генерирует breadcrumb структурированные данные"""
        breadcrumb_list = {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": []
        }
        
        for idx, item in enumerate(items, start=1):
            breadcrumb_list["itemListElement"].append({
                "@type": "ListItem",
                "position": idx,
                "name": item.get('name', ''),
                "item": item.get('url', '')
            })
        
        return breadcrumb_list



