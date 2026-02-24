from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from services.admin_service import AdminService
from services.dream_service import DreamService

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.before_request
def check_admin():
    # Only allow if explicitly logged in as 'admin' role
    if not current_user.is_authenticated or current_user.role != 'admin':
        return redirect('/')

@admin_bp.route('/')
def dashboard():
    stats = AdminService.get_stats()
    # For Dashboard we only need general lists, but we can also have a 'moderation mode'
    all_dreams = DreamService.get_all_dreams_admin()
    withdrawals = AdminService.get_pending_withdrawals()
    
    # Получаем пользователей для отображения
    search = request.args.get('search', '')
    status_filter = request.args.get('status', '')
    role_filter = request.args.get('role', '')
    page = int(request.args.get('page', 1))
    limit = 20
    offset = (page - 1) * limit
    
    users_data = AdminService.get_all_users(
        search=search if search else None,
        status=status_filter if status_filter else None,
        role=role_filter if role_filter else None,
        limit=limit,
        offset=offset
    )
    
    return render_template('admin.html', 
                         stats=stats, 
                         withdrawals=withdrawals, 
                         all_dreams=all_dreams,
                         users_data=users_data,
                         current_page=page,
                         search=search,
                         status_filter=status_filter,
                         role_filter=role_filter)

@admin_bp.route('/moderate/next')
def moderate_next():
    # Get one pending dream
    dreams = AdminService.get_pending_dreams()
    if not dreams:
        return jsonify({'empty': True})
    
    dream = dreams[0]
    return jsonify({
        'empty': False,
        'dream': dream.to_dict(user=current_user),
        'author_phone': dream.author.phone,
        'author_telegram': dream.author.telegram or 'Нет'
    })

@admin_bp.route('/dream/<int:id>/<action>')
def moderate(id, action):
    result = DreamService.moderate_dream(id, action)
    if request.args.get('ajax'):
        dream = DreamService.get_dream_by_id(id)
        return jsonify({'success': result, 'is_verified': dream.is_admin_verified if dream else False})
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/dream/update', methods=['POST'])
def update_dream():
    id = request.form.get('id')
    data = {
        'title': request.form.get('title'),
        'price': request.form.get('price'),
        'category': request.form.get('category'),
        'desc': request.form.get('desc'),
        'is_verified': request.form.get('is_verified') == 'on'
    }
    image = request.files.get('image')
    
    DreamService.update_dream(id, data, image)
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/withdraw/<int:id>/<action>')
def moderate_withdraw(id, action):
    if action == 'approve':
        AdminService.approve_withdrawal(id)
    elif action == 'reject':
        AdminService.reject_withdrawal(id)
    return redirect(url_for('admin.dashboard'))

# ========== USER MANAGEMENT ROUTES ==========

@admin_bp.route('/users')
def users_list():
    """API: Получить список пользователей"""
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    role = request.args.get('role', '')
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 20))
    offset = (page - 1) * limit
    
    users_data = AdminService.get_all_users(
        search=search if search else None,
        status=status if status else None,
        role=role if role else None,
        limit=limit,
        offset=offset
    )
    
    users_list = []
    for user in users_data['users']:
        users_list.append({
            'id': user.id,
            'username': user.username,
            'name': user.name,
            'phone': user.phone,
            'telegram': user.telegram,
            'role': user.role,
            'status': user.status,
            'balance': user.balance,
            'earned_balance': user.earned_balance,
            'is_verified': user.is_verified,
            'avatar_url': user.avatar_url or f"https://api.dicebear.com/7.x/avataaars/svg?seed={user.avatar_seed}",
            'avatar_seed': user.avatar_seed,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'dreams_count': len(user.dreams) if user.dreams else 0
        })
    
    return jsonify({
        'success': True,
        'users': users_list,
        'total': users_data['total'],
        'page': page,
        'limit': limit
    })

@admin_bp.route('/user/<int:user_id>')
def get_user(user_id):
    """API: Получить данные пользователя"""
    user = AdminService.get_user_by_id(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'Пользователь не найден'}), 404
    
    dreams = AdminService.get_user_dreams(user_id)
    
    return jsonify({
        'success': True,
        'user': {
            'id': user.id,
            'username': user.username,
            'name': user.name,
            'phone': user.phone,
            'telegram': user.telegram,
            'bio': user.bio,
            'role': user.role,
            'status': user.status,
            'balance': user.balance,
            'earned_balance': user.earned_balance,
            'is_verified': user.is_verified,
            'is_anon_pref': user.is_anon_pref,
            'is_private': user.is_private,
            'hide_fulfilled_public': user.hide_fulfilled_public,
            'avatar_url': user.avatar_url or f"https://api.dicebear.com/7.x/avataaars/svg?seed={user.avatar_seed}",
            'avatar_seed': user.avatar_seed,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'last_login': user.last_login.isoformat() if user.last_login else None
        },
        'dreams': [d.to_dict() for d in dreams],
        'dreams_count': len(dreams)
    })

@admin_bp.route('/user/<int:user_id>/update', methods=['POST'])
def update_user(user_id):
    """Обновить данные пользователя"""
    data = {}
    
    if request.is_json:
        data = request.json
    else:
        # Form data
        data = {
            'username': request.form.get('username'),
            'name': request.form.get('name'),
            'phone': request.form.get('phone'),
            'telegram': request.form.get('telegram'),
            'bio': request.form.get('bio'),
            'role': request.form.get('role'),
            'status': request.form.get('status'),
            'balance': request.form.get('balance'),
            'earned_balance': request.form.get('earned_balance'),
            'is_verified': request.form.get('is_verified'),
            'is_anon_pref': request.form.get('is_anon_pref'),
            'is_private': request.form.get('is_private'),
            'hide_fulfilled_public': request.form.get('hide_fulfilled_public'),
            'avatar_seed': request.form.get('avatar_seed')
        }
        
        # Обработка загрузки аватара
        avatar_file = request.files.get('avatar')
        if avatar_file and avatar_file.filename:
            success, error = AdminService.update_user_avatar(user_id, avatar_file)
            if not success:
                if request.is_json:
                    return jsonify({'success': False, 'message': error}), 400
                flash(f'Ошибка загрузки аватара: {error}', 'error')
                return redirect(url_for('admin.dashboard'))
    
    success, error = AdminService.update_user(user_id, data)
    if success:
        # Проверяем, это AJAX запрос (через заголовок или параметр)
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.args.get('ajax'):
            return jsonify({'success': True})
        flash('Пользователь обновлен', 'success')
    else:
        # Проверяем, это AJAX запрос
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.args.get('ajax'):
            return jsonify({'success': False, 'message': error}), 400
        flash(f'Ошибка: {error}', 'error')
    
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/user/<int:user_id>/avatar/delete', methods=['POST'])
def delete_user_avatar(user_id):
    """Удалить аватар пользователя"""
    success, error = AdminService.delete_user_avatar(user_id)
    if success:
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': error}), 400

@admin_bp.route('/user/<int:user_id>/avatar/update', methods=['POST'])
def update_user_avatar(user_id):
    """Обновить аватар пользователя"""
    avatar_file = request.files.get('avatar')
    if not avatar_file:
        return jsonify({'success': False, 'message': 'Файл не загружен'}), 400
    
    success, error = AdminService.update_user_avatar(user_id, avatar_file)
    if success:
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': error}), 400

@admin_bp.route('/user/<int:user_id>/block', methods=['POST'])
def block_user(user_id):
    """Заблокировать пользователя"""
    success = AdminService.block_user(user_id)
    if success:
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Пользователь не найден'}), 404

@admin_bp.route('/user/<int:user_id>/unblock', methods=['POST'])
def unblock_user(user_id):
    """Разблокировать пользователя"""
    success = AdminService.unblock_user(user_id)
    if success:
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Пользователь не найден'}), 404

@admin_bp.route('/user/<int:user_id>/dreams')
def get_user_dreams(user_id):
    """Получить мечты пользователя"""
    dreams = AdminService.get_user_dreams(user_id)
    return jsonify({
        'success': True,
        'dreams': [d.to_dict() for d in dreams]
    })

@admin_bp.route('/user/<int:user_id>/dream/<int:dream_id>/delete', methods=['POST'])
def delete_user_dream(user_id, dream_id):
    """Удалить мечту пользователя"""
    success, error = AdminService.delete_user_dream(dream_id)
    if success:
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': error}), 400

@admin_bp.route('/user/<int:user_id>/dreams/delete-all', methods=['POST'])
def delete_all_user_dreams(user_id):
    """Удалить все мечты пользователя"""
    confirm = request.json.get('confirm', False) if request.is_json else request.form.get('confirm', False)
    if not confirm:
        return jsonify({'success': False, 'message': 'Требуется подтверждение'}), 400
    
    success, count = AdminService.delete_all_user_dreams(user_id)
    if success:
        return jsonify({'success': True, 'deleted_count': count})
    return jsonify({'success': False, 'message': 'Ошибка удаления'}), 400

@admin_bp.route('/user/<int:user_id>/delete', methods=['POST'])
def delete_user(user_id):
    """Полностью удалить пользователя"""
    confirm = request.json.get('confirm', False) if request.is_json else request.form.get('confirm', False)
    if not confirm:
        return jsonify({'success': False, 'message': 'Требуется подтверждение'}), 400
    
    success, error = AdminService.delete_user(user_id)
    if success:
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': error}), 400
