from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from services.finance_service import FinanceService

pay_bp = Blueprint('pay', __name__)

@pay_bp.route('/create', methods=['POST'])
@login_required
def create_payment():
    amount = float(request.json.get('amount', 0))
    if amount < 100:
        return jsonify({'success': False, 'message': 'Минимум 100₽'})
        
    success, result = FinanceService.create_topup(current_user.id, amount)
    if success:
        return jsonify({'success': True, 'pay_url': result['pay_url'], 'expires_at': result['expires_at']})
    return jsonify({'success': False, 'message': result})

@pay_bp.route('/check', methods=['POST'])
@login_required
def check_status():
    FinanceService.check_pending_transactions(current_user.id)
    return jsonify({'success': True, 'balance': current_user.balance})

@pay_bp.route('/pending', methods=['GET'])
@login_required
def get_pending():
    """Получить информацию о текущей незавершенной транзакции"""
    pending = FinanceService.get_pending_transaction(current_user.id)
    if pending:
        return jsonify({'success': True, 'transaction': pending})
    return jsonify({'success': False})

@pay_bp.route('/withdraw', methods=['POST'])
@login_required
def withdraw():
    amount = float(request.json.get('amount', 0))
    details = request.json.get('details', '')
    
    if amount < 500:
        return jsonify({'success': False, 'message': 'Минимум 500₽ для вывода'})
        
    success, msg = FinanceService.create_withdrawal_request(current_user.id, amount, details)
    return jsonify({'success': success, 'message': msg})
