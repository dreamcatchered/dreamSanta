from models import User, Dream, Transaction, WithdrawalRequest, db
from sqlalchemy import or_

class AdminService:
    @staticmethod
    def get_stats():
        total_users = User.query.count()
        total_dreams = Dream.query.count()
        fulfilled_dreams = Dream.query.filter_by(status='fulfilled').count()
        # System balance excludes admin money usually, but here simple sum
        total_balance = db.session.query(db.func.sum(User.balance)).scalar() or 0
        
        return {
            "users": total_users,
            "dreams": total_dreams,
            "fulfilled": fulfilled_dreams,
            "system_balance": total_balance
        }

    @staticmethod
    def get_pending_dreams():
        return Dream.query.filter_by(status='pending').order_by(Dream.created_at.asc()).all()

    @staticmethod
    def get_pending_withdrawals():
        return WithdrawalRequest.query.filter_by(status='pending').order_by(WithdrawalRequest.created_at.asc()).all()

    @staticmethod
    def approve_withdrawal(req_id):
        req = db.session.get(WithdrawalRequest, req_id)
        if req:
            req.status = 'paid'
            # Money was already deducted from balance when request was created.
            db.session.commit()
            
            # Создаем уведомление
            from services.notification_service import NotificationService
            NotificationService.notify_withdrawal(req.user_id, req.amount, 'paid', req_id)
            
            return True
        return False
        
    @staticmethod
    def reject_withdrawal(req_id):
        req = db.session.get(WithdrawalRequest, req_id)
        if req:
            req.status = 'rejected'
            # Refund user
            req.user.balance += req.amount
            req.user.earned_balance += req.amount # Return to earned as it was earned
            db.session.commit()
            
            # Создаем уведомление
            from services.notification_service import NotificationService
            NotificationService.notify_withdrawal(req.user_id, req.amount, 'rejected', req_id)
            
            return True
        return False

    @staticmethod
    def block_user(user_id):
        user = db.session.get(User, user_id)
        if user:
            user.status = 'blocked'
            db.session.commit()
            return True
        return False

    @staticmethod
    def unblock_user(user_id):
        user = db.session.get(User, user_id)
        if user:
            user.status = 'active'
            db.session.commit()
            return True
        return False

    # ========== USER MANAGEMENT ==========
    
    @staticmethod
    def get_all_users(search=None, status=None, role=None, limit=50, offset=0):
        """Получить всех пользователей с фильтрацией и пагинацией"""
        query = User.query
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    User.username.ilike(search_term),
                    User.name.ilike(search_term),
                    User.phone.ilike(search_term),
                    User.telegram.ilike(search_term)
                )
            )
        
        if status:
            query = query.filter_by(status=status)
        
        if role:
            query = query.filter_by(role=role)
        
        total = query.count()
        users = query.order_by(User.created_at.desc()).limit(limit).offset(offset).all()
        
        return {
            'users': users,
            'total': total,
            'limit': limit,
            'offset': offset
        }

    @staticmethod
    def get_user_by_id(user_id):
        """Получить пользователя по ID со всей информацией"""
        return db.session.get(User, user_id)

    @staticmethod
    def update_user(user_id, data):
        """Обновить данные пользователя"""
        user = db.session.get(User, user_id)
        if not user:
            return False, "Пользователь не найден"
        
        # Обновляем поля
        if 'username' in data and data['username']:
            # Проверяем уникальность
            existing = User.query.filter_by(username=data['username']).first()
            if existing and existing.id != user_id:
                return False, "Логин уже занят"
            user.username = data['username']
        
        if 'name' in data:
            user.name = data['name']
        
        if 'phone' in data:
            # Проверяем уникальность телефона
            if data['phone']:
                existing = User.query.filter_by(phone=data['phone']).first()
                if existing and existing.id != user_id:
                    return False, "Телефон уже занят"
            user.phone = data['phone']
        
        if 'telegram' in data:
            user.telegram = data['telegram']
        
        if 'bio' in data:
            user.bio = data['bio']
        
        if 'role' in data and data['role'] in ['dreamer', 'santa', 'admin']:
            user.role = data['role']
        
        if 'status' in data and data['status'] in ['active', 'blocked']:
            user.status = data['status']
        
        if 'is_verified' in data:
            user.is_verified = data['is_verified'] == True or data['is_verified'] == 'true'
        
        if 'is_anon_pref' in data:
            user.is_anon_pref = data['is_anon_pref'] == True or data['is_anon_pref'] == 'true'
        
        if 'is_private' in data:
            user.is_private = data['is_private'] == True or data['is_private'] == 'true'
        
        if 'hide_fulfilled_public' in data:
            user.hide_fulfilled_public = data['hide_fulfilled_public'] == True or data['hide_fulfilled_public'] == 'true'
        
        if 'balance' in data:
            try:
                user.balance = float(data['balance'])
            except:
                pass
        
        if 'earned_balance' in data:
            try:
                user.earned_balance = float(data['earned_balance'])
            except:
                pass
        
        if 'avatar_seed' in data:
            user.avatar_seed = data['avatar_seed']
            user.avatar_url = None  # Сбрасываем загруженную аватарку
        
        db.session.commit()
        return True, None

    @staticmethod
    def delete_user_avatar(user_id):
        """Удалить аватар пользователя"""
        user = db.session.get(User, user_id)
        if not user:
            return False, "Пользователь не найден"
        
        # Удаляем файл, если он существует
        if user.avatar_url:
            import os
            from config import Config
            file_path = user.avatar_url.replace('/static/', '')
            full_path = os.path.join('static', file_path)
            if os.path.exists(full_path):
                try:
                    os.remove(full_path)
                except:
                    pass
        
        user.avatar_url = None
        # Устанавливаем дефолтный seed, если его нет
        if not user.avatar_seed:
            user.avatar_seed = "Santa"
        
        db.session.commit()
        return True, None

    @staticmethod
    def update_user_avatar(user_id, avatar_file):
        """Обновить аватар пользователя"""
        from services.dream_service import DreamService
        
        user = db.session.get(User, user_id)
        if not user:
            return False, "Пользователь не найден"
        
        # Удаляем старый аватар
        if user.avatar_url:
            import os
            file_path = user.avatar_url.replace('/static/', '')
            full_path = os.path.join('static', file_path)
            if os.path.exists(full_path):
                try:
                    os.remove(full_path)
                except:
                    pass
        
        # Сохраняем новый
        path = DreamService.save_image(avatar_file)
        if path:
            user.avatar_url = path
            db.session.commit()
            return True, None
        
        return False, "Ошибка сохранения изображения"

    @staticmethod
    def get_user_dreams(user_id, limit=100):
        """Получить все мечты пользователя"""
        return Dream.query.filter_by(user_id=user_id).order_by(Dream.created_at.desc()).limit(limit).all()

    @staticmethod
    def delete_user_dream(dream_id):
        """Удалить мечту пользователя"""
        dream = db.session.get(Dream, dream_id)
        if not dream:
            return False, "Мечта не найдена"
        
        # Удаляем изображение, если оно локальное
        if dream.image_url and dream.image_url.startswith('/static/'):
            import os
            file_path = dream.image_url.replace('/static/', '')
            full_path = os.path.join('static', file_path)
            if os.path.exists(full_path):
                try:
                    os.remove(full_path)
                except:
                    pass
        
        db.session.delete(dream)
        db.session.commit()
        return True, None

    @staticmethod
    def delete_all_user_dreams(user_id):
        """Удалить все мечты пользователя"""
        dreams = Dream.query.filter_by(user_id=user_id).all()
        count = 0
        
        for dream in dreams:
            # Удаляем изображения
            if dream.image_url and dream.image_url.startswith('/static/'):
                import os
                file_path = dream.image_url.replace('/static/', '')
                full_path = os.path.join('static', file_path)
                if os.path.exists(full_path):
                    try:
                        os.remove(full_path)
                    except:
                        pass
            
            db.session.delete(dream)
            count += 1
        
        db.session.commit()
        return True, count

    @staticmethod
    def delete_user(user_id):
        """Полностью удалить пользователя и все его данные"""
        user = db.session.get(User, user_id)
        if not user:
            return False, "Пользователь не найден"
        
        # Нельзя удалить админа
        if user.role == 'admin':
            return False, "Нельзя удалить администратора"
        
        # Удаляем аватар
        if user.avatar_url:
            import os
            file_path = user.avatar_url.replace('/static/', '')
            full_path = os.path.join('static', file_path)
            if os.path.exists(full_path):
                try:
                    os.remove(full_path)
                except:
                    pass
        
        # Удаляем все мечты пользователя (и их изображения)
        dreams = Dream.query.filter_by(user_id=user_id).all()
        for dream in dreams:
            if dream.image_url and dream.image_url.startswith('/static/'):
                import os
                file_path = dream.image_url.replace('/static/', '')
                full_path = os.path.join('static', file_path)
                if os.path.exists(full_path):
                    try:
                        os.remove(full_path)
                    except:
                        pass
        
        # SQLAlchemy cascade удалит связанные записи (dreams, transactions, etc.)
        db.session.delete(user)
        db.session.commit()
        
        return True, None
