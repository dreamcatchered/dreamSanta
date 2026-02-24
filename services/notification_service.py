# -*- coding: utf-8 -*-
"""
Сервис для работы с уведомлениями
"""
from models import Notification, db
from utils.timezone import now_msk, msk_to_utc

class NotificationService:
    @staticmethod
    def create(user_id, title, message, type='info', related_id=None):
        """Создать уведомление"""
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=type,
            related_id=related_id
        )
        db.session.add(notification)
        db.session.commit()
        return notification

    @staticmethod
    def get_unread_count(user_id):
        """Получить количество непрочитанных уведомлений"""
        return Notification.query.filter_by(user_id=user_id, is_read=False).count()

    @staticmethod
    def get_all(user_id, limit=50):
        """Получить все уведомления пользователя"""
        return Notification.query.filter_by(user_id=user_id).order_by(Notification.created_at.desc()).limit(limit).all()

    @staticmethod
    def mark_read(notification_id, user_id):
        """Отметить уведомление как прочитанное"""
        notification = db.session.get(Notification, notification_id)
        if notification and notification.user_id == user_id:
            notification.is_read = True
            db.session.commit()
            return True
        return False

    @staticmethod
    def mark_all_read(user_id):
        """Отметить все уведомления как прочитанные"""
        Notification.query.filter_by(user_id=user_id, is_read=False).update({'is_read': True})
        db.session.commit()
        return True

    @staticmethod
    def notify_dream_moderated(user_id, dream_id, dream_title, status):
        """Уведомление о модерации мечты"""
        if status == 'approved':
            title = "🎉 Мечта одобрена!"
            message = f'Ваша мечта "{dream_title}" прошла модерацию и теперь доступна всем!'
        elif status == 'rejected':
            title = "❌ Мечта отклонена"
            message = f'К сожалению, ваша мечта "{dream_title}" была отклонена модератором.'
        else:
            return
        return NotificationService.create(user_id, title, message, 'dream_moderated', dream_id)

    @staticmethod
    def notify_dream_fulfilled(user_id, dream_id, dream_title):
        """Уведомление об исполнении мечты"""
        title = "✨ Мечта исполнена!"
        message = f'Ваша мечта "{dream_title}" была исполнена! Проверьте баланс.'
        return NotificationService.create(user_id, title, message, 'dream_fulfilled', dream_id)

    @staticmethod
    def notify_balance_topup(user_id, amount, transaction_id=None):
        """Уведомление о пополнении баланса"""
        title = "💰 Баланс пополнен"
        message = f'Ваш баланс пополнен на {amount:.2f} ₽'
        return NotificationService.create(user_id, title, message, 'balance_topup', transaction_id)

    @staticmethod
    def notify_withdrawal(user_id, amount, status, withdrawal_id=None):
        """Уведомление о статусе заявки на вывод"""
        if status == 'paid':
            title = "✅ Вывод одобрен"
            message = f'Ваша заявка на вывод {amount:.2f} ₽ была одобрена и обработана.'
        elif status == 'rejected':
            title = "❌ Вывод отклонен"
            message = f'Ваша заявка на вывод {amount:.2f} ₽ была отклонена. Средства возвращены на баланс.'
        else:
            return
        return NotificationService.create(user_id, title, message, 'withdrawal', withdrawal_id)



