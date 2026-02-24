import os
from werkzeug.utils import secure_filename
from models import Dream, db, Like, UserHistory, User
from datetime import datetime
from services.user_service import UserService
from config import Config
from utils.timezone import now_msk, msk_to_utc
from utils.image_compression import compress_image, should_compress

class DreamService:
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

    @staticmethod
    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in DreamService.ALLOWED_EXTENSIONS

    @staticmethod
    def save_image(file):
        if file and DreamService.allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_name = f"{int(now_msk().timestamp())}_{filename}"
            path = os.path.join(Config.UPLOAD_FOLDER, unique_name)
            os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
            
            # Проверяем, нужно ли сжимать изображение
            if should_compress(file):
                compressed = compress_image(file, max_size_mb=5, quality=85)
                if compressed:
                    # Определяем расширение
                    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'jpg'
                    if ext not in ('jpg', 'jpeg', 'png'):
                        ext = 'jpg'  # Конвертируем в JPEG
                    
                    # Обновляем имя файла с правильным расширением
                    unique_name = f"{int(now_msk().timestamp())}_{filename.rsplit('.', 1)[0]}.{ext}"
                    path = os.path.join(Config.UPLOAD_FOLDER, unique_name)
                    
                    # Сохраняем сжатое изображение
                    with open(path, 'wb') as f:
                        f.write(compressed.read())
                else:
                    # Если сжатие не удалось, сохраняем оригинал
                    file.seek(0)
                    file.save(path)
            else:
                file.seek(0)
                file.save(path)
            
            return f"/static/uploads/{unique_name}"
        return None

    @staticmethod
    def create_dream(user_id, data, image_file=None):
        image_url = 'https://images.unsplash.com/photo-1510557880182-3d4d3cba35a5?w=400'
        if image_file:
            saved_path = DreamService.save_image(image_file)
            if saved_path:
                image_url = saved_path
        
        dream = Dream(
            user_id=user_id,
            title=data.get('title'),
            price=float(data.get('price')),
            category=data.get('category'),
            description=data.get('desc', ''),
            reason=data.get('reason', ''),
            image_url=image_url
        )
        db.session.add(dream)
        db.session.flush()
        UserService.log_action(user_id, "Новая мечта", f"Создана мечта: {dream.title}", related_id=dream.id, type="dream")
        db.session.commit()
        return dream

    @staticmethod
    def update_dream(dream_id, data, image_file=None):
        """Admin update method"""
        dream = db.session.get(Dream, dream_id)
        if not dream: return False
        
        if data.get('title'): dream.title = data['title']
        if data.get('price'): dream.price = float(data['price'])
        if data.get('category'): dream.category = data['category']
        if data.get('desc'): dream.description = data['desc']
        if 'is_verified' in data:
            dream.is_admin_verified = data['is_verified'] == 'true' or data['is_verified'] is True
        
        if image_file:
            saved_path = DreamService.save_image(image_file)
            if saved_path:
                dream.image_url = saved_path
                
        db.session.commit()
        return True

    @staticmethod
    def get_active_dreams(category='Все', sort='likes', limit=50, current_user_id=None, exclude_hidden=False):
        """
        Получить активные мечты
        
        Args:
            category: категория мечты
            sort: сортировка ('likes', 'hot', 'new')
            limit: лимит результатов
            current_user_id: ID текущего пользователя (для проверки лайков)
            exclude_hidden: если True, исключает мечты скрытые из публичного профиля
        """
        query = Dream.query.filter_by(status='approved')
        if category != 'Все':
            query = query.filter_by(category=category)
        
        # Исключаем скрытые мечты, если exclude_hidden=True
        if exclude_hidden:
            query = query.filter((Dream.hide_from_public == False) | (Dream.hide_from_public == None))
        
        if sort == 'likes':
            query = query.order_by(Dream.likes_count.desc(), Dream.created_at.desc())
        elif sort == 'hot':
            query = query.order_by(Dream.views_count.desc())
        else:
            query = query.order_by(Dream.created_at.desc())
            
        dreams = query.limit(limit).all()
        
        # Attach 'liked' status for current user if authenticated
        if current_user_id:
            user_likes = Like.query.filter_by(user_id=current_user_id).all()
            liked_dream_ids = {like.dream_id for like in user_likes}
            for dream in dreams:
                dream.liked = dream.id in liked_dream_ids
            return dreams
        
        return dreams
        
    @staticmethod
    def get_all_dreams_admin():
        # Get active and pending for admin dashboard
        return Dream.query.order_by(Dream.created_at.desc()).all()

    @staticmethod
    def get_user_dreams(user_id):
        return Dream.query.filter_by(user_id=user_id).order_by(Dream.created_at.desc()).all()

    @staticmethod
    def get_dream_by_id(dream_id, current_user_id=None):
        dream = db.session.get(Dream, dream_id)
        if dream:
            dream.views_count += 1
            db.session.commit()
            
            # Устанавливаем liked статус, если пользователь авторизован
            if current_user_id:
                user_likes = Like.query.filter_by(user_id=current_user_id).all()
                liked_dream_ids = {like.dream_id for like in user_likes}
                dream.liked = dream.id in liked_dream_ids
        return dream

    @staticmethod
    def increment_view(dream_id):
        dream = db.session.get(Dream, dream_id)
        if dream:
            dream.views_count += 1
            db.session.commit()
        return dream

    @staticmethod
    def toggle_like(user_id, dream_id):
        existing = Like.query.filter_by(user_id=user_id, dream_id=dream_id).first()
        dream = db.session.get(Dream, dream_id)
        if not dream: return False, 0
        
        if existing:
            db.session.delete(existing)
            dream.likes_count = max(0, dream.likes_count - 1)
            action = "unliked"
        else:
            new_like = Like(user_id=user_id, dream_id=dream_id)
            db.session.add(new_like)
            dream.likes_count += 1
            action = "liked"
        db.session.commit()
        return action, dream.likes_count

    @staticmethod
    def fulfill_dream(santa_id, dream_id, is_anon=False):
        santa = db.session.get(User, santa_id)
        dream = db.session.get(Dream, dream_id)
        
        if not santa or not dream: return False, "Ошибка данных"
        if santa.balance < dream.price: return False, "Недостаточно средств"
        if dream.status != 'approved': return False, "Мечта уже исполнена или на модерации"
        if dream.user_id == santa_id: return False, "Нельзя исполнить свою мечту"

        # Check global anonymity pref of Santa
        if santa.is_anon_pref:
            is_anon = True

        santa.balance -= dream.price
        if santa.balance < santa.earned_balance:
            santa.earned_balance = santa.balance
        
        dreamer = db.session.get(User, dream.user_id)
        dreamer.balance += dream.price
        dreamer.earned_balance += dream.price 
        
        dream.status = 'fulfilled'
        dream.fulfilled_by = santa_id
        dream.fulfilled_at = msk_to_utc(now_msk())
        
        santa_name = "Анонимный Санта" if is_anon else santa.name
        
        UserService.log_action(santa_id, "Чудо", f"Исполнена мечта: {dream.title} (-{dream.price}₽)", related_id=dream.id, type="dream")
        UserService.log_action(dream.user_id, "Мечта сбылась!", f"{santa_name} исполнил мечту: {dream.title} (+{dream.price}₽)", related_id=dream.id, type="dream")
        
        # Создаем уведомление для автора мечты
        from services.notification_service import NotificationService
        NotificationService.notify_dream_fulfilled(dream.user_id, dream_id, dream.title)
        
        db.session.commit()
        return True, "Мечта исполнена!"

    @staticmethod
    def get_fulfilled_dreams(limit=10):
        return Dream.query.filter_by(status='fulfilled').order_by(Dream.fulfilled_at.desc()).limit(limit).all()

    @staticmethod
    def get_fulfilled_dreams_by_user(user_id):
        """Получить мечты, исполненные данным пользователем"""
        return Dream.query.filter_by(fulfilled_by=user_id, status='fulfilled').order_by(Dream.fulfilled_at.desc()).all()

    @staticmethod
    def moderate_dream(dream_id, action, comment=None):
        dream = db.session.get(Dream, dream_id)
        if not dream: return False
        
        if action == 'approve':
            dream.status = 'approved'
            # Создаем уведомление о модерации
            from services.notification_service import NotificationService
            NotificationService.notify_dream_moderated(dream.user_id, dream_id, dream.title, 'approved')
        elif action == 'reject':
            dream.status = 'rejected'
            dream.moderator_comment = comment
            # Создаем уведомление об отклонении
            from services.notification_service import NotificationService
            NotificationService.notify_dream_moderated(dream.user_id, dream_id, dream.title, 'rejected')
        elif action == 'delete':
            db.session.delete(dream)
        elif action == 'verify':
            dream.is_admin_verified = not dream.is_admin_verified  # Toggle
            
        db.session.commit()
        return True
