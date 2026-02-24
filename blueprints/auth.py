from flask import Blueprint, request, jsonify, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from services.user_service import UserService
from utils.sms_service import DreamSMS

auth_bp = Blueprint('auth', __name__)
sms_service = DreamSMS()

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    user = UserService.get_by_username(username)
    
    if user and user.check_password(password):
        if user.status == 'blocked':
            return jsonify({'success': False, 'message': 'Ваш аккаунт заблокирован'})
            
        login_user(user)
        UserService.log_action(user.id, "Вход", "Авторизация в системе", type="system")
        return jsonify({'success': True})
        
    return jsonify({'success': False, 'message': 'Неверный логин или пароль'})

@auth_bp.route('/send-code', methods=['POST'])
def send_code():
    phone = request.json.get('phone')
    if not phone: 
        return jsonify({'success': False, 'message': 'Введите номер телефона'})
    
    # Нормализуем номер (убираем пробелы и другие символы)
    phone = phone.strip()
    if not phone.startswith('+7'): 
        return jsonify({'success': False, 'message': 'Только номера РФ (+7...)'})
    
    # Check if phone already taken
    if UserService.get_by_phone(phone):
        return jsonify({'success': False, 'message': 'Этот номер уже используется'})

    import random
    code = str(random.randint(100000, 999999))
    res = sms_service.send_code(phone, code)
    
    if res.get('success'):
        return jsonify({'success': True})
    
    # Используем сообщение об ошибке из API или дефолтное
    error_message = res.get('message', 'Ошибка отправки кода. Попробуйте позже.')
    return jsonify({'success': False, 'message': error_message})

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    name = data.get('name')
    phone = data.get('phone')
    code = data.get('code')
    
    if not all([username, password, name, phone, code]):
        return jsonify({'success': False, 'message': 'Заполните все поля'})
        
    # Verify Code First
    sms_res = sms_service.verify_code(phone, code)
    if not sms_res.get('success'):
        # Используем сообщение об ошибке из API или дефолтное
        error_message = sms_res.get('message', 'Неверный код. Проверьте код из Telegram и попробуйте снова.')
        return jsonify({'success': False, 'message': error_message})

    user, error = UserService.create_user(username, password, name, phone)
    if error:
        return jsonify({'success': False, 'message': error})
        
    login_user(user)
    return jsonify({'success': True})

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@auth_bp.route('/api/user/me')
@login_required
def get_me():
    return jsonify(current_user.to_dict())
