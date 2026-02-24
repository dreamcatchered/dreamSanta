# -*- coding: utf-8 -*-
"""
SEO контекстный процессор для Flask
Автоматически добавляет SEO данные в контекст шаблонов
"""
from flask import request, has_request_context
from seo.seo_utils import SEOGenerator


def seo_context_processor():
    """Контекстный процессор для добавления SEO данных в шаблоны"""
    if not has_request_context():
        return {}
    
    base_seo = {
        'seo_base_url': SEOGenerator.BASE_URL,
        'seo_site_name': SEOGenerator.SITE_NAME,
        'seo_current_url': f"{SEOGenerator.BASE_URL}{request.path}",
        'seo_default_image': SEOGenerator.DEFAULT_IMAGE,
        'seo_default_description': SEOGenerator.DEFAULT_DESCRIPTION
    }
    
    return base_seo

