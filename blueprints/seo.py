# -*- coding: utf-8 -*-
"""
SEO Blueprint - для генерации sitemap, robots.txt и других SEO файлов
"""
from flask import Blueprint, render_template, Response, jsonify
from seo.seo_utils import SEOGenerator
from models import Dream, User
from extensions import db
from datetime import datetime

seo_bp = Blueprint('seo', __name__)


@seo_bp.route('/sitemap.xml')
def sitemap():
    """Генерация sitemap.xml"""
    base_url = SEOGenerator.BASE_URL
    
    # Статические страницы
    static_pages = [
        {'loc': f'{base_url}/', 'changefreq': 'daily', 'priority': '1.0'},
        {'loc': f'{base_url}/app', 'changefreq': 'daily', 'priority': '0.9'},
        {'loc': f'{base_url}/rules', 'changefreq': 'monthly', 'priority': '0.7'},
        {'loc': f'{base_url}/about', 'changefreq': 'monthly', 'priority': '0.7'},
    ]
    
    # Активные мечты
    active_dreams = Dream.query.filter_by(status='approved').limit(500).all()
    for dream in active_dreams:
        static_pages.append({
            'loc': f'{base_url}/app#dream={dream.id}',
            'changefreq': 'weekly',
            'priority': '0.8',
            'lastmod': dream.created_at.strftime('%Y-%m-%d') if dream.created_at else None
        })
    
    # Публичные профили
    public_users = User.query.filter_by(is_private=False).limit(500).all()
    for user in public_users:
        static_pages.append({
            'loc': f'{base_url}/@{user.username}',
            'changefreq': 'weekly',
            'priority': '0.7',
            'lastmod': user.last_login.strftime('%Y-%m-%d') if user.last_login else None
        })
    
    sitemap_xml = render_template('sitemap.xml', pages=static_pages, base_url=base_url)
    return Response(sitemap_xml, mimetype='application/xml')


@seo_bp.route('/robots.txt')
def robots():
    """Возвращает robots.txt"""
    robots_content = """User-agent: *
Allow: /
Disallow: /admin/
Disallow: /auth/
Disallow: /api/
Disallow: /pay/

# Sitemap
Sitemap: https://santa.dreampartners.online/sitemap.xml
"""
    return Response(robots_content, mimetype='text/plain')

