from models import User, db, UserHistory
from datetime import datetime
from config import Config
import os
from werkzeug.utils import secure_filename

class UserService:
    @staticmethod
    def create_user(username, password, name, phone):
        if User.query.filter_by(username=username).first():
            return None, "Логин уже занят"
        if User.query.filter_by(phone=phone).first():
            return None, "Телефон уже занят"
        
        # Hardcoded Admin Rule
        role = 'dreamer'
        if phone == '+79654222325':
            role = 'admin'

        user = User(username=username, name=name, phone=phone, role=role, is_verified=True)
        user.set_password(password)
        
        # Random avatar seed
        import random
        seeds = ["Santa", "Elf", "Deer", "Snowman", "Cookie"]
        user.avatar_seed = random.choice(seeds) + str(random.randint(1, 100))
        
        db.session.add(user)
        db.session.commit()
        
        if role == 'admin':
            UserService.log_action(user.id, "Система", "Назначен администратором (по номеру)", type="system")
        
        UserService.log_action(user.id, "Регистрация", "Добро пожаловать в сказку!")
        return user, None

    @staticmethod
    def get_by_id(user_id):
        return db.session.get(User, user_id)
        
    @staticmethod
    def get_by_username(username):
        return User.query.filter_by(username=username).first()

    @staticmethod
    def get_by_phone(phone):
        return User.query.filter_by(phone=phone).first()

    @staticmethod
    def update_profile(user_id, name=None, username=None, bio=None, role=None, avatar_file=None, avatar_seed=None, is_anon=None, telegram=None, is_private=None, hide_fulfilled_public=None):
        user = db.session.get(User, user_id)
        if not user: return False, "User not found"
        
        if username and username != user.username:
            if User.query.filter_by(username=username).first():
                return False, "Логин занят"
            user.username = username

        if name: user.name = name
        if bio: user.bio = bio
        if telegram is not None: user.telegram = telegram
        if role: user.role = role
        if is_anon is not None: user.is_anon_pref = is_anon
        if is_private is not None: user.is_private = is_private
        if hide_fulfilled_public is not None: user.hide_fulfilled_public = hide_fulfilled_public
        
        if avatar_seed: 
            user.avatar_seed = avatar_seed
            user.avatar_url = None 
        
        if avatar_file:
            from services.dream_service import DreamService
            path = DreamService.save_image(avatar_file)
            if path:
                user.avatar_url = path
        
        db.session.commit()
        return user, None

    @staticmethod
    def log_action(user_id, action, details="", related_id=None, type="system"):
        history = UserHistory(
            user_id=user_id, 
            action=action, 
            details=details,
            related_id=related_id,
            type=type
        )
        db.session.add(history)
        db.session.commit()

    @staticmethod
    def get_history(user_id):
        return UserHistory.query.filter_by(user_id=user_id).order_by(UserHistory.created_at.desc()).all()

    @staticmethod
    def change_role(user_id, new_role):
        user = db.session.get(User, user_id)
        if user:
            user.role = new_role
            db.session.commit()
            return True
        return False
