from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from App.controllers import (
    create_user,
    get_all_users,
    get_all_users_json,
)

user_views = Blueprint('user_views', __name__, template_folder='../templates')

@user_views.route('/api/users', methods=['GET'])
def get_users_action():
    users = get_all_users_json()
    return jsonify(users)

@user_views.route('/api/users', methods=['POST'])
def create_user_endpoint():
    data = request.json
    user = create_user(data['username'], data['password'])
    return jsonify({'message': f"user {user.username} created with id {user.id}"})

@user_views.route('/api/staff', methods=['GET'])
@jwt_required()
def get_staff_api():
    """Get all active help desk assistants for scheduling"""
    try:
        from App.models import HelpDeskAssistant, Student
        
        # Get all active assistants
        assistants = HelpDeskAssistant.query.filter_by(active=True).all()
        
        # Format the data
        staff_list = []
        for assistant in assistants:
            student = Student.query.get(assistant.username)
            
            if student:
                staff_list.append({
                    'id': assistant.username,
                    'name': student.name if student.name else assistant.username,
                    'degree': student.degree
                })
        
        return jsonify({'success': True, 'staff': staff_list})
    except Exception as e:
        print(f"Error fetching staff: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500