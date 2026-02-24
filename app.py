from flask import Flask, render_template
from config import Config
from extensions import db, login_manager
from models import User, Dream

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'index'
    
    # SEO Context Processor
    try:
        from seo.seo_context import seo_context_processor
        app.context_processor(seo_context_processor)
    except ImportError:
        print("⚠️ SEO модуль не найден, SEO функции будут недоступны")

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register Blueprints
    from blueprints.auth import auth_bp
    from blueprints.api import api_bp
    from blueprints.payments import pay_bp
    from blueprints.admin import admin_bp
    from blueprints.seo import seo_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(pay_bp, url_prefix='/pay')
    app.register_blueprint(admin_bp)
    app.register_blueprint(seo_bp)  # SEO routes (sitemap, robots.txt)

    # Main Routes
    @app.route('/')
    def index():
        from services.dream_service import DreamService
        # Получаем активные мечты (исключая скрытые из публичного профиля)
        active_dreams = DreamService.get_active_dreams(limit=6, exclude_hidden=True)
        top_fulfilled = DreamService.get_fulfilled_dreams(6)
        return render_template('index.html', top_fulfilled=top_fulfilled, active_dreams=active_dreams)

    @app.route('/app')
    def app_page():
        return render_template('app.html')

    @app.route('/rules')
    def rules():
        return render_template('rules.html')

    @app.route('/about')
    def about():
        return render_template('about.html')

    @app.template_filter('format_rub')
    def format_rub(value):
        try:
            return "{:,.2f}".format(float(value)).replace(",", " ").replace(".", ",") + " ₽"
        except:
            return str(value) + " ₽"
    
    @app.template_filter('date_iso')
    def date_iso(value):
        """Конвертирует datetime в ISO формат для sitemap"""
        if value:
            if hasattr(value, 'isoformat'):
                return value.isoformat()
            return str(value)
        return None

    def render_public_profile(username):
        """Вспомогательная функция для отображения публичного профиля"""
        from flask_login import current_user
        from services.user_service import UserService
        from services.dream_service import DreamService
        
        user = UserService.get_by_username(username)
        if not user:
            return None, 404
        
        # Проверка приватности профиля
        if user.is_private:
            # Если профиль приватный, показывать только владельцу
            if not current_user.is_authenticated or current_user.id != user.id:
                return None, 'private'  # Специальный код для приватного профиля
            
        dreams = DreamService.get_user_dreams(user.id)
        fulfilled_gifts = DreamService.get_fulfilled_dreams_by_user(user.id)
        
        # Фильтруем исполненные мечты если включена настройка
        if hasattr(user, 'hide_fulfilled_public') and user.hide_fulfilled_public:
            dreams = [d for d in dreams if d.status != 'fulfilled']
            fulfilled_gifts = []  # Также скрываем исполненные подарки
        
        # Фильтруем мечты скрытые из публичного профиля (и созданные, и исполненные)
        dreams = [d for d in dreams if not (hasattr(d, 'hide_from_public') and d.hide_from_public)]
        fulfilled_gifts = [g for g in fulfilled_gifts if not (hasattr(g, 'hide_from_public') and g.hide_from_public)]
        
        return render_template('public_profile.html', user=user, dreams=dreams, fulfilled_gifts=fulfilled_gifts, current_user=current_user), None

    @app.route('/@<username>')
    def public_profile_with_at(username):
        result, error = render_public_profile(username)
        if error == 404:
            return "Пользователь не найден", 404
        elif error == 'private':
            return render_template('private_profile.html'), 403
        return result

    @app.route('/<username>')
    def public_profile(username):
        # Проверяем, что это не зарезервированный маршрут
        reserved = ['app', 'rules', 'about', 'admin', 'auth', 'api', 'pay', 'static', 'favicon.ico']
        if username in reserved:
            return "Страница не найдена", 404
        
        result, error = render_public_profile(username)
        if error == 404:
            return "Пользователь не найден", 404
        elif error == 'private':
            return render_template('private_profile.html'), 403
        return result

    # Setup database
    with app.app_context():
        db.create_all()
        
        # Миграция: добавляем недостающие поля
        try:
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            
            # Миграция для users
            columns = [col['name'] for col in inspector.get_columns('users')]
            if 'hide_fulfilled_public' not in columns:
                with db.engine.connect() as conn:
                    conn.execute(text('ALTER TABLE users ADD COLUMN hide_fulfilled_public BOOLEAN DEFAULT 0'))
                    conn.commit()
                print("✅ Миграция: добавлено поле hide_fulfilled_public")
            
            # Миграция для dreams
            dream_columns = [col['name'] for col in inspector.get_columns('dreams')]
            if 'hide_from_public' not in dream_columns:
                with db.engine.connect() as conn:
                    conn.execute(text('ALTER TABLE dreams ADD COLUMN hide_from_public BOOLEAN DEFAULT 0'))
                    conn.commit()
                print("✅ Миграция: добавлено поле hide_from_public")
                
        except Exception as e:
            print(f"⚠️ Ошибка миграции (может уже существовать): {e}")
        
        # Admin is now handled dynamically via phone number +79654222325 in UserService

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)

