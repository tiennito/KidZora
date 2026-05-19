from functools import wraps
from flask import flash, redirect, url_for, session, request, jsonify
from flask_login import current_user, login_required
from app.models.profile import Profile

def role_required(*roles):
    """Decorator to require specific user roles"""
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            if not current_user.is_active():
                flash('Your account has been banned. Please contact support.', 'error')
                return redirect(url_for('auth.logout'))
            
            if current_user.role not in roles:
                flash('You do not have permission to access this page.', 'error')
                return redirect(url_for('auth.dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    """Decorator to require admin role"""
    return role_required('admin')(f)

def seller_required(f):
    """Decorator to require seller role"""
    return role_required('seller')(f)

def buyer_required(f):
    """Decorator to require buyer role"""
    return role_required('buyer')(f)

def rider_required(f):
    """Decorator to require rider role"""
    return role_required('rider')(f)

def approval_required(f):
    """Decorator to require user approval (for sellers and riders)"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        
        if not current_user.is_active():
            flash('Your account has been banned. Please contact support.', 'error')
            return redirect(url_for('auth.logout'))
        
        if current_user.role in ['seller', 'rider'] and not current_user.is_approved:
            flash('Your account is pending approval. Please wait for admin approval.', 'warning')
            return redirect(url_for('auth.pending_approval'))
        
        return f(*args, **kwargs)
    return decorated_function

def api_role_required(*roles):
    """Decorator for API endpoints requiring specific roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check for JWT token or session
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({'error': 'Authorization token required'}), 401
            
            token = auth_header.split(' ')[1]
            try:
                # Verify token with Supabase
                from app.extensions import supabase
                user_response = supabase.auth.get_user(token)
                user_data = user_response.user
                
                if not user_data:
                    return jsonify({'error': 'Invalid token'}), 401
                
                # Get user profile
                profile = Profile.get_by_id(user_data.id)
                if not profile:
                    return jsonify({'error': 'User profile not found'}), 404
                
                if not profile.is_active():
                    return jsonify({'error': 'Account is banned'}), 403
                
                if profile.role not in roles:
                    return jsonify({'error': 'Insufficient permissions'}), 403
                
                # Add user to request context
                request.current_user = profile
                return f(*args, **kwargs)
                
            except Exception as e:
                return jsonify({'error': 'Token verification failed'}), 401
        
        return decorated_function
    return decorator

def api_admin_required(f):
    """Decorator for API endpoints requiring admin role"""
    return api_role_required('admin')(f)

def api_seller_required(f):
    """Decorator for API endpoints requiring seller role"""
    return api_role_required('seller')(f)

def api_buyer_required(f):
    """Decorator for API endpoints requiring buyer role"""
    return api_role_required('buyer')(f)

def api_rider_required(f):
    """Decorator for API endpoints requiring rider role"""
    return api_role_required('rider')(f)
