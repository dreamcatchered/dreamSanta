from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from services.dream_service import DreamService
from services.user_service import UserService

api_bp = Blueprint('api', __name__)

@api_bp.route('/dreams', methods=['GET'])
def get_dreams():
    category = request.args.get('category', 'Все')
    current_user_id = current_user.id if current_user.is_authenticated else None
    # В ленте мечт исключаем скрытые из публичного профиля (если пользователь не автор)
    exclude_hidden = True  # Всегда исключаем скрытые мечты из публичной ленты
    dreams = DreamService.get_active_dreams(category=category, current_user_id=current_user_id, exclude_hidden=exclude_hidden)
    return jsonify([d.to_dict(user=current_user) for d in dreams])

@api_bp.route('/dreams/create', methods=['POST'])
@login_required
def create_dream():
    image = request.files.get('image')
    data = request.form
    try:
        dream = DreamService.create_dream(current_user.id, data, image)
        return jsonify({'success': True, 'dream': dream.to_dict(user=current_user)})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@api_bp.route('/dreams/<int:dream_id>', methods=['GET'])
def get_dream_detail(dream_id):
    current_user_id = current_user.id if current_user.is_authenticated else None
    dream = DreamService.get_dream_by_id(dream_id, current_user_id=current_user_id)
    if dream:
        return jsonify(dream.to_dict(user=current_user))
    return jsonify({'error': 'Not found'}), 404

@api_bp.route('/dreams/<int:dream_id>/like', methods=['POST'])
@login_required
def like_dream(dream_id):
    action, count = DreamService.toggle_like(current_user.id, dream_id)
    return jsonify({'success': True, 'action': action, 'likes': count})

@api_bp.route('/dreams/<int:dream_id>/delete', methods=['POST'])
@login_required
def delete_dream(dream_id):
    dream = DreamService.get_dream_by_id(dream_id)
    if not dream:
        return jsonify({'success': False, 'message': 'Мечта не найдена'}), 404
    
    if dream.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Нет доступа'}), 403
    
    if dream.status == 'fulfilled':
        return jsonify({'success': False, 'message': 'Нельзя удалить исполненную мечту'}), 400
    
    DreamService.moderate_dream(dream_id, 'delete')
    from services.user_service import UserService
    UserService.log_action(current_user.id, "Удаление мечты", f"Удалена мечта: {dream.title}", type="dream")
    return jsonify({'success': True, 'message': 'Мечта удалена'})

@api_bp.route('/dreams/<int:dream_id>/toggle-public', methods=['POST'])
@login_required
def toggle_dream_public(dream_id):
    """Переключить видимость мечты в публичном профиле"""
    from models import Dream, db
    
    try:
        dream = db.session.get(Dream, dream_id)
        if not dream:
            print(f"Dream {dream_id} not found")
            return jsonify({'success': False, 'message': 'Мечта не найдена'}), 404
        
        # Пользователь может управлять видимостью, если он создатель ИЛИ исполнитель мечты
        is_owner = dream.user_id == current_user.id
        is_fulfiller = dream.fulfilled_by == current_user.id if dream.fulfilled_by else False
        
        print(f"Dream {dream_id}: owner={dream.user_id}, current_user={current_user.id}, is_owner={is_owner}, fulfilled_by={dream.fulfilled_by}, is_fulfiller={is_fulfiller}")
        
        if not (is_owner or is_fulfiller):
            print(f"Access denied for user {current_user.id} to dream {dream_id}")
            return jsonify({'success': False, 'message': 'Нет доступа'}), 403
        
        # Переключаем видимость
        old_value = dream.hide_from_public if hasattr(dream, 'hide_from_public') else False
        dream.hide_from_public = not old_value
        
        db.session.commit()
        
        print(f"Dream {dream_id} visibility toggled: {old_value} -> {dream.hide_from_public}")
        
        return jsonify({
            'success': True, 
            'hide_from_public': dream.hide_from_public,
            'message': 'Видимость обновлена'
        })
    except Exception as e:
        print(f"Error in toggle_dream_public: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Ошибка сервера: {str(e)}'}), 500

@api_bp.route('/dreams/<int:dream_id>/buy', methods=['POST'])
@login_required
def buy_dream(dream_id):
    is_anon = request.json.get('is_anonymous', False)
    success, msg = DreamService.fulfill_dream(current_user.id, dream_id, is_anon)
    return jsonify({'success': success, 'message': msg})

@api_bp.route('/profile/history')
@login_required
def get_history():
    history = UserService.get_history(current_user.id)
    return jsonify([h.to_dict() for h in history])

@api_bp.route('/profile/dreams')
@login_required
def get_my_dreams():
    from models import Dream
    # Получаем мечты, созданные пользователем
    created_dreams = DreamService.get_user_dreams(current_user.id)
    # Получаем мечты, исполненные пользователем
    fulfilled_dreams = Dream.query.filter_by(fulfilled_by=current_user.id).all()
    
    # Объединяем и убираем дубликаты (на случай, если пользователь исполнил свою же мечту)
    all_dreams_dict = {}
    for dream in created_dreams:
        dream.is_owned = True  # Мечта создана пользователем
        dream.is_fulfilled_by_me = False  # Не исполнена пользователем (он создатель)
        all_dreams_dict[dream.id] = dream
    
    for dream in fulfilled_dreams:
        if dream.id not in all_dreams_dict:
            dream.is_owned = False  # Мечта не создана пользователем
            dream.is_fulfilled_by_me = True  # Исполнена пользователем
            all_dreams_dict[dream.id] = dream
        else:
            # Если пользователь и создал, и исполнил мечту
            all_dreams_dict[dream.id].is_fulfilled_by_me = True
    
    all_dreams = list(all_dreams_dict.values())
    # Сортируем по дате создания/исполнения
    all_dreams.sort(key=lambda x: x.created_at, reverse=True)
    
    # Добавляем информацию о лайках пользователя
    from models import Like
    user_likes = Like.query.filter_by(user_id=current_user.id).all()
    liked_dream_ids = {like.dream_id for like in user_likes}
    for dream in all_dreams:
        dream.liked = dream.id in liked_dream_ids
    
    # Преобразуем в словари с дополнительной информацией
    result = []
    for d in all_dreams:
        dream_dict = d.to_dict(user=current_user)
        dream_dict['is_owned'] = getattr(d, 'is_owned', False)
        dream_dict['is_fulfilled_by_me'] = getattr(d, 'is_fulfilled_by_me', False)
        # Пользователь может управлять видимостью, если это его мечта ИЛИ он её исполнил
        dream_dict['can_manage_visibility'] = dream_dict['is_owned'] or dream_dict['is_fulfilled_by_me']
        result.append(dream_dict)
    
    return jsonify(result)

@api_bp.route('/user/role', methods=['POST'])
@login_required
def change_role():
    role = request.json.get('role')
    if role in ['santa', 'dreamer']:
        UserService.change_role(current_user.id, role)
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Invalid role'})

@api_bp.route('/user/profile', methods=['POST'])
@login_required
def update_profile():
    data = request.json
    name = data.get('name')
    username = data.get('username')
    bio = data.get('bio')
    is_anon = data.get('is_anon')
    is_private = data.get('is_private')
    hide_fulfilled_public = data.get('hide_fulfilled_public')
    
    user, err = UserService.update_profile(current_user.id, name=name, username=username, bio=bio, is_anon=is_anon, is_private=is_private, hide_fulfilled_public=hide_fulfilled_public)
    if err:
        return jsonify({'success': False, 'message': err})
    return jsonify({'success': True})

@api_bp.route('/user/avatar', methods=['POST'])
@login_required
def update_avatar():
    file = request.files.get('avatar')
    if file:
        UserService.update_profile(current_user.id, avatar_file=file)
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'No file'})

@api_bp.route('/user/avatar-gen', methods=['POST'])
@login_required
def generate_avatar():
    seed = request.json.get('seed')
    if seed:
        UserService.update_profile(current_user.id, avatar_seed=seed)
        return jsonify({'success': True})
    return jsonify({'success': False})

@api_bp.route('/notifications', methods=['GET'])
@login_required
def get_notifications():
    from services.notification_service import NotificationService
    notifications = NotificationService.get_all(current_user.id)
    return jsonify([n.to_dict() for n in notifications])

@api_bp.route('/notifications/unread', methods=['GET'])
@login_required
def get_unread_count():
    from services.notification_service import NotificationService
    count = NotificationService.get_unread_count(current_user.id)
    return jsonify({'count': count})

@api_bp.route('/notifications/<int:notif_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notif_id):
    from services.notification_service import NotificationService
    success = NotificationService.mark_read(notif_id, current_user.id)
    return jsonify({'success': success})

@api_bp.route('/notifications/read-all', methods=['POST'])
@login_required
def mark_all_read():
    from services.notification_service import NotificationService
    NotificationService.mark_all_read(current_user.id)
    return jsonify({'success': True})
