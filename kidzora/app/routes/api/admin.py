from flask import Blueprint, request, jsonify
from app.utils.decorators import api_admin_required
from app.models.profile import Profile
from app.models.seller import Seller
from app.models.rider import Rider
from app.models.coupon import Coupon
from app.models.transaction import Transaction
from app.models.message import Message
from datetime import datetime

admin_api_bp = Blueprint('admin_api', __name__)

@admin_api_bp.route('/users/pending', methods=['GET'])
@api_admin_required
def get_pending_users():
    """Get pending sellers and riders"""
    pending_sellers = Profile.get_all({'role': 'seller', 'is_approved': False})
    pending_riders = Profile.get_all({'role': 'rider', 'is_approved': False})
    
    # Format response
    sellers_data = []
    for seller in pending_sellers:
        seller_details = Seller.get_by_user_id(seller.id)
        sellers_data.append({
            'id': seller.id,
            'name': seller.get_full_name(),
            'email': seller.email,
            'phone': seller.phone,
            'shop_name': seller_details.shop_name if seller_details else None,
            'created_at': seller.created_at
        })
    
    riders_data = []
    for rider in pending_riders:
        rider_details = Rider.get_by_user_id(rider.id)
        riders_data.append({
            'id': rider.id,
            'name': rider.get_full_name(),
            'email': rider.email,
            'phone': rider.phone,
            'vehicle_type': rider_details.vehicle_type if rider_details else None,
            'vehicle_plate': rider_details.vehicle_plate if rider_details else None,
            'created_at': rider.created_at
        })
    
    return jsonify({
        'sellers': sellers_data,
        'riders': riders_data
    })

@admin_api_bp.route('/users/<user_id>/approve', methods=['POST'])
@api_admin_required
def approve_user_api(user_id):
    """Approve user registration"""
    user = Profile.get_by_id(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    if user.update({'is_approved': True}):
        return jsonify({'message': 'User approved successfully'})
    else:
        return jsonify({'error': 'Failed to approve user'}), 500

@admin_api_bp.route('/users/<user_id>/ban', methods=['POST'])
@api_admin_required
def ban_user_api(user_id):
    """Ban user"""
    user = Profile.get_by_id(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    if user.update({'is_banned': True}):
        return jsonify({'message': 'User banned successfully'})
    else:
        return jsonify({'error': 'Failed to ban user'}), 500

@admin_api_bp.route('/commission', methods=['GET'])
@api_admin_required
def get_commission_data():
    """Get commission data"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    commission_data = Transaction.get_commission_summary(start_date, end_date)
    
    return jsonify({
        'total_commission': commission_data['total_commission'],
        'total_earnings': commission_data['total_earnings'],
        'transaction_count': commission_data['transaction_count']
    })

@admin_api_bp.route('/reports', methods=['GET'])
@api_admin_required
def generate_report_api():
    """Generate report"""
    report_type = request.args.get('type', 'sales')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date or not end_date:
        return jsonify({'error': 'Start date and end date are required'}), 400
    
    # Generate report data based on type
    report_data = {}
    
    if report_type == 'sales':
        # Sales report logic
        report_data = {'message': 'Sales report data'}
    elif report_type == 'users':
        # User report logic
        all_users = Profile.get_all()
        report_data = {
            'total_users': len(all_users),
            'admins': len([u for u in all_users if u.role == 'admin']),
            'sellers': len([u for u in all_users if u.role == 'seller']),
            'buyers': len([u for u in all_users if u.role == 'buyer']),
            'riders': len([u for u in all_users if u.role == 'rider'])
        }
    elif report_type == 'commissions':
        report_data = Transaction.get_commission_summary(start_date, end_date)
    
    return jsonify(report_data)

@admin_api_bp.route('/coupons', methods=['POST'])
@api_admin_required
def create_coupon_api():
    """Create coupon"""
    data = request.get_json()
    
    coupon_data = {
        'code': data.get('code', '').upper(),
        'description': data.get('description'),
        'discount_type': data.get('discount_type'),
        'discount_value': float(data.get('discount_value')),
        'min_order_amount': float(data.get('min_order_amount', 0)),
        'max_discount_amount': float(data.get('max_discount_amount')) if data.get('max_discount_amount') else None,
        'usage_limit': int(data.get('usage_limit')) if data.get('usage_limit') else None,
        'expires_at': data.get('expires_at'),
        'is_active': data.get('is_active', True)
    }
    
    coupon = Coupon.create(coupon_data)
    if coupon:
        return jsonify({'message': 'Coupon created successfully', 'coupon_id': coupon.id})
    else:
        return jsonify({'error': 'Failed to create coupon'}), 500

@admin_api_bp.route('/coupons/<int:coupon_id>', methods=['PUT'])
@api_admin_required
def update_coupon_api(coupon_id):
    """Update coupon"""
    coupon = Coupon.get_by_id(coupon_id)
    if not coupon:
        return jsonify({'error': 'Coupon not found'}), 404
    
    data = request.get_json()
    
    update_data = {}
    if 'description' in data:
        update_data['description'] = data['description']
    if 'discount_type' in data:
        update_data['discount_type'] = data['discount_type']
    if 'discount_value' in data:
        update_data['discount_value'] = float(data['discount_value'])
    if 'min_order_amount' in data:
        update_data['min_order_amount'] = float(data['min_order_amount'])
    if 'max_discount_amount' in data:
        update_data['max_discount_amount'] = float(data['max_discount_amount']) if data['max_discount_amount'] else None
    if 'usage_limit' in data:
        update_data['usage_limit'] = int(data['usage_limit']) if data['usage_limit'] else None
    if 'expires_at' in data:
        update_data['expires_at'] = data['expires_at']
    if 'is_active' in data:
        update_data['is_active'] = data['is_active']
    
    if coupon.update(update_data):
        return jsonify({'message': 'Coupon updated successfully'})
    else:
        return jsonify({'error': 'Failed to update coupon'}), 500

@admin_api_bp.route('/coupons/<int:coupon_id>', methods=['DELETE'])
@api_admin_required
def delete_coupon_api(coupon_id):
    """Delete coupon"""
    coupon = Coupon.get_by_id(coupon_id)
    if not coupon:
        return jsonify({'error': 'Coupon not found'}), 404
    
    if coupon.delete():
        return jsonify({'message': 'Coupon deleted successfully'})
    else:
        return jsonify({'error': 'Failed to delete coupon'}), 500

@admin_api_bp.route('/messages/<seller_id>', methods=['GET'])
@api_admin_required
def get_conversation_api(seller_id):
    """Get conversation with seller"""
    seller = Profile.get_by_id(seller_id)
    if not seller or seller.role != 'seller':
        return jsonify({'error': 'Seller not found'}), 404
    
    # Get current admin user ID from request context
    admin_id = request.current_user.id
    
    messages = Message.get_conversation(admin_id, seller_id)
    
    messages_data = []
    for message in messages:
        messages_data.append({
            'id': message.id,
            'sender_id': message.sender_id,
            'receiver_id': message.receiver_id,
            'content': message.content,
            'message_type': message.message_type,
            'is_read': message.is_read,
            'created_at': message.created_at
        })
    
    return jsonify({'messages': messages_data})
