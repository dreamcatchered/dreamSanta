from datetime import datetime
from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from utils.timezone import now_msk, msk_to_utc

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), unique=True, nullable=True) 
    username = db.Column(db.String(100), unique=True, nullable=False) 
    password_hash = db.Column(db.String(255), nullable=True) 
    telegram = db.Column(db.String(100)) # Новое: Telegram для связи
    name = db.Column(db.String(100), default="Счастливчик")
    bio = db.Column(db.Text, default="Мечтаю о чудесах...")
    
    avatar_seed = db.Column(db.String(50), default="Santa")
    avatar_url = db.Column(db.String(255)) # Новое: Загруженная аватарка
    
    balance = db.Column(db.Float, default=0.0) # Общий баланс
    earned_balance = db.Column(db.Float, default=0.0) # Новое: Средства, доступные к выводу (подаренные)
    
    role = db.Column(db.String(20), default='dreamer') 
    status = db.Column(db.String(20), default='active') 
    is_verified = db.Column(db.Boolean, default=False) 
    is_anon_pref = db.Column(db.Boolean, default=False) # Настройка анонимности
    is_private = db.Column(db.Boolean, default=False) # Анонимный (не общедоступный) профиль
    hide_fulfilled_public = db.Column(db.Boolean, default=False) # Скрывать исполненные мечты в публичном профиле
    
    last_login = db.Column(db.DateTime, default=lambda: msk_to_utc(now_msk()))
    created_at = db.Column(db.DateTime, default=lambda: msk_to_utc(now_msk()))
    
    dreams = db.relationship('Dream', backref='author', lazy=True, cascade="all, delete-orphan", foreign_keys='Dream.user_id')
    fulfilled_dreams = db.relationship('Dream', backref='santa', lazy=True, foreign_keys='Dream.fulfilled_by')
    transactions = db.relationship('Transaction', backref='user', lazy=True)
    likes = db.relationship('Like', backref='user', lazy=True)
    history = db.relationship('UserHistory', backref='user', lazy=True)
    withdrawals = db.relationship('WithdrawalRequest', backref='user', lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy=True, cascade="all, delete-orphan", order_by='Notification.created_at.desc()')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash: return False
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "phone": self.phone,
            "name": self.name,
            "balance": self.balance,
            "earned": self.earned_balance, 
            "role": self.role,
            "is_anon": self.is_anon_pref,
            "is_private": self.is_private,
            "hide_fulfilled_public": self.hide_fulfilled_public,
            "telegram": self.telegram,
            "avatar": self.avatar_url or f"https://api.dicebear.com/7.x/avataaars/svg?seed={self.avatar_seed}",
            "bio": self.bio
        }

class Dream(db.Model):
    __tablename__ = 'dreams'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    reason = db.Column(db.Text)
    category = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(500))
    
    status = db.Column(db.String(20), default='pending') 
    moderator_comment = db.Column(db.String(255))
    is_admin_verified = db.Column(db.Boolean, default=False) # Новое: Галочка от админа
    hide_from_public = db.Column(db.Boolean, default=False) # Скрыть конкретную мечту из публичного профиля
    
    views_count = db.Column(db.Integer, default=0)
    likes_count = db.Column(db.Integer, default=0)
    
    is_hot = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: msk_to_utc(now_msk()))
    fulfilled_at = db.Column(db.DateTime)
    fulfilled_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    likes = db.relationship('Like', backref='dream', lazy=True, cascade="all, delete-orphan")

    def to_dict(self, user=None):
        fulfilled_by_name = None
        if self.fulfilled_by and self.santa:
            fulfilled_by_name = self.santa.name

        # Mapping status to Russian
        status_map = {
            'pending': 'На модерации',
            'approved': 'Активно',
            'rejected': 'Отклонено',
            'fulfilled': 'Исполнено'
        }

        # Используем уже установленное значение liked (если было установлено в get_active_dreams)
        # Иначе проверяем через relationship
        liked = getattr(self, 'liked', False)
        if not liked and user and hasattr(user, 'is_authenticated') and user.is_authenticated:
            liked = any(l.user_id == user.id for l in self.likes)

        return {
            "id": self.id,
            "user_id": self.user_id,  # Добавляем user_id для проверки владельца
            "title": self.title,
            "price": self.price,
            "category": self.category,
            "image": self.image_url,
            "desc": self.description,
            "reason": self.reason,
            "author": self.author.name,
            "authorUsername": self.author.username,
            "authorAvatar": self.author.avatar_url or f"https://api.dicebear.com/7.x/avataaars/svg?seed={self.author.avatar_seed}",
            "views": self.views_count,
            "likes": self.likes_count,
            "liked": liked,
            "status": self.status,
            "status_ru": status_map.get(self.status, self.status),
            "fulfilled_by": fulfilled_by_name,
            "is_verified": self.is_admin_verified,
            "hide_from_public": self.hide_from_public if hasattr(self, 'hide_from_public') else False,
            "created_at": self.created_at.isoformat()
        }

class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount_rub = db.Column(db.Float, nullable=False)
    amount_usdt = db.Column(db.Float)
    type = db.Column(db.String(20)) 
    status = db.Column(db.String(20), default='pending') 
    external_id = db.Column(db.String(100), unique=True)
    payment_url = db.Column(db.String(500))
    expires_at = db.Column(db.DateTime)  # Время истечения счета (МСК + 1 час)
    created_at = db.Column(db.DateTime, default=lambda: msk_to_utc(now_msk()))

class WithdrawalRequest(db.Model):
    __tablename__ = 'withdrawals'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    details = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')
    admin_comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: msk_to_utc(now_msk()))

class Like(db.Model):
    __tablename__ = 'likes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    dream_id = db.Column(db.Integer, db.ForeignKey('dreams.id'), nullable=False)

class UserHistory(db.Model):
    __tablename__ = 'user_history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(255))
    details = db.Column(db.Text)
    related_id = db.Column(db.Integer) 
    type = db.Column(db.String(20)) 
    created_at = db.Column(db.DateTime, default=lambda: msk_to_utc(now_msk()))

    def to_dict(self):
        from utils.timezone import utc_to_msk
        created_msk = utc_to_msk(self.created_at) if self.created_at.tzinfo else self.created_at
        return {
            "id": self.id,
            "date": created_msk.strftime("%d.%m"),
            "desc": self.action,
            "details": self.details,
            "related_id": self.related_id,
            "type": self.type
        }

class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50))  # 'dream_moderated', 'dream_fulfilled', 'balance_topup', 'withdrawal'
    is_read = db.Column(db.Boolean, default=False)
    related_id = db.Column(db.Integer)  # ID связанного объекта (dream_id, transaction_id, etc.)
    created_at = db.Column(db.DateTime, default=lambda: msk_to_utc(now_msk()))

    def to_dict(self):
        from utils.timezone import utc_to_msk
        created_msk = utc_to_msk(self.created_at) if self.created_at.tzinfo else self.created_at
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "type": self.type,
            "is_read": self.is_read,
            "related_id": self.related_id,
            "created_at": created_msk.isoformat(),
            "time_ago": self._get_time_ago(created_msk)
        }
    
    def _get_time_ago(self, dt):
        """Возвращает человекочитаемое время назад"""
        from utils.timezone import now_msk, MSK_TZ, utc_to_msk
        import pytz
        
        if dt is None:
            return "Недавно"
        
        now = now_msk()
        
        # Конвертируем dt в MSK для корректного сравнения
        try:
            if dt.tzinfo is None:
                # Если нет timezone, считаем что это UTC из БД
                dt_utc = pytz.utc.localize(dt)
                dt_msk = utc_to_msk(dt_utc)
            else:
                # Если есть timezone, конвертируем в MSK
                dt_msk = utc_to_msk(dt) if hasattr(dt.tzinfo, 'zone') and 'UTC' in str(dt.tzinfo) else dt.astimezone(MSK_TZ)
        except:
            # В случае ошибки используем простой подход
            try:
                dt_msk = utc_to_msk(dt)
            except:
                # Последний fallback - убираем timezone и сравниваем
                now_naive = now.replace(tzinfo=None) if now.tzinfo else now
                dt_naive = dt.replace(tzinfo=None) if dt.tzinfo else dt
                diff_seconds = (now_naive - dt_naive).total_seconds()
                days = int(diff_seconds // 86400)
                if days > 0:
                    return f"{days} дн. назад"
                hours = int(diff_seconds // 3600)
                if hours > 0:
                    return f"{hours} ч. назад"
                minutes = int(diff_seconds // 60)
                if minutes > 0:
                    return f"{minutes} мин. назад"
                return "Только что"
        
        # Убеждаемся что оба datetime в MSK
        if now.tzinfo is None:
            now = MSK_TZ.localize(now)
        elif now.tzinfo != MSK_TZ:
            now = now.astimezone(MSK_TZ)
            
        if dt_msk.tzinfo is None:
            dt_msk = MSK_TZ.localize(dt_msk)
        elif dt_msk.tzinfo != MSK_TZ:
            dt_msk = dt_msk.astimezone(MSK_TZ)
        
        # Вычисляем разницу
        diff = now - dt_msk
        diff_seconds = diff.total_seconds()
        
        days = int(diff_seconds // 86400)
        if days > 0:
            return f"{days} дн. назад"
        hours = int(diff_seconds // 3600)
        if hours > 0:
            return f"{hours} ч. назад"
        minutes = int(diff_seconds // 60)
        if minutes > 0:
            return f"{minutes} мин. назад"
        return "Только что"
