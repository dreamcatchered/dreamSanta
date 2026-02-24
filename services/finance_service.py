from models import Transaction, User, db, WithdrawalRequest
from utils.crypto_bot import CryptoBotAPI
from config import Config
from services.user_service import UserService
from utils.timezone import now_msk, msk_to_utc
from utils.usdt_rate import get_cached_usdt_rate
from datetime import timedelta

class FinanceService:
    crypto_api = CryptoBotAPI(Config.CRYPTO_BOT_TOKEN)

    @staticmethod
    def create_topup(user_id, amount_rub):
        user = db.session.get(User, user_id)
        if not user: return False, "User not found"
        
        # Получаем актуальный курс USDT/RUB онлайн
        usdt_rate = get_cached_usdt_rate()
        if not usdt_rate:
            return False, "Ошибка получения курса валют. Попробуйте позже."
        
        amount_usdt = amount_rub / usdt_rate
        
        result = FinanceService.crypto_api.create_invoice(
            amount_usdt=amount_usdt,
            description=f"TopUp Santa Market (UID: {user_id})",
            user_id=user_id
        )
        
        if result.get('ok'):
            invoice = result['result']
            # Время истечения: 1 час от текущего времени МСК
            expires_at = now_msk() + timedelta(hours=1)
            tx = Transaction(
                user_id=user_id,
                amount_rub=amount_rub,
                amount_usdt=amount_usdt,
                type='deposit',
                status='pending',
                external_id=str(invoice['invoice_id']),
                payment_url=invoice['pay_url'],
                expires_at=msk_to_utc(expires_at)
            )
            db.session.add(tx)
            db.session.commit()
            return True, {'pay_url': invoice['pay_url'], 'expires_at': expires_at.isoformat()}
        
        return False, result.get('error')

    @staticmethod
    def check_pending_transactions(user_id):
        """Check status of pending transactions for user"""
        from utils.timezone import utc_to_msk
        pending_txs = Transaction.query.filter_by(user_id=user_id, status='pending', type='deposit').all()
        updated_count = 0
        current_msk = now_msk()
        
        for tx in pending_txs:
            # Проверяем истечение времени (1 час МСК)
            if tx.expires_at:
                expires_msk = utc_to_msk(tx.expires_at)
                if current_msk > expires_msk:
                    tx.status = 'failed'
                    db.session.commit()
                    continue
            
            status = FinanceService.crypto_api.check_invoice_status(tx.external_id)
            if status == 'paid':
                tx.status = 'completed'
                # Add money to user
                user = db.session.get(User, user_id)
                user.balance += tx.amount_rub
                # Earned balance does NOT increase on deposit
                
                UserService.log_action(user_id, "Пополнение", f"+{tx.amount_rub}₽ (Crypto)")
                
                # Создаем уведомление о пополнении
                from services.notification_service import NotificationService
                NotificationService.notify_balance_topup(user_id, tx.amount_rub, tx.id)
                
                updated_count += 1
            elif status in ['expired', 'deleted']:
                tx.status = 'failed'
                
        if updated_count > 0:
            db.session.commit()
            return True
        return False
    
    @staticmethod
    def get_pending_transaction(user_id):
        """Получить текущую незавершенную транзакцию пользователя"""
        from utils.timezone import utc_to_msk
        pending_tx = Transaction.query.filter_by(user_id=user_id, status='pending', type='deposit').order_by(Transaction.created_at.desc()).first()
        if pending_tx and pending_tx.expires_at:
            expires_msk = utc_to_msk(pending_tx.expires_at)
            current_msk = now_msk()
            if current_msk > expires_msk:
                pending_tx.status = 'failed'
                db.session.commit()
                return None
            return {
                'pay_url': pending_tx.payment_url,
                'expires_at': expires_msk.isoformat(),
                'amount': pending_tx.amount_rub
            }
        return None

    @staticmethod
    def create_withdrawal_request(user_id, amount, details):
        user = db.session.get(User, user_id)
        
        # AML Check: Can only withdraw earned balance
        if amount > user.earned_balance:
            return False, f"Доступно к выводу только {user.earned_balance}₽ (подаренные средства)"
            
        if user.balance < amount:
            return False, "Недостаточно средств на балансе"
        
        # Deduct balance immediately
        user.balance -= amount
        user.earned_balance -= amount
        
        req = WithdrawalRequest(
            user_id=user_id,
            amount=amount,
            details=details,
            status='pending'
        )
        db.session.add(req)
        UserService.log_action(user_id, "Заявка на вывод", f"-{amount}₽ (Ожидание)", type="system")
        db.session.commit()
        return True, "Заявка создана"

