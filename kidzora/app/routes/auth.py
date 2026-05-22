import os
import random
import re
import string
import smtplib
import ssl
import requests as http_requests
from werkzeug.utils import secure_filename
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.models.profile import Profile
from app.extensions import supabase, supabase_admin
from app.services.two_factor import (
    decrypt_secret,
    encrypt_secret,
    new_totp_secret,
    provisioning_uri,
    qr_data_uri,
    verify_totp,
)

ALLOWED_DOC_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

def _allowed_doc(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_DOC_EXTENSIONS

def save_seller_file(file, user_id, file_type):
    """Upload a seller registration document to Supabase Storage; return public URL or None."""
    if not file or file.filename == '':
        return None
    if not _allowed_doc(file.filename):
        return None
    from app.extensions import supabase_admin
    from app.utils.images import upload_to_storage, upload_raw_to_storage, is_image_ext
    ext          = file.filename.rsplit('.', 1)[1].lower()
    filename     = secure_filename(f"{file_type}_{user_id}.{ext}")
    storage_path = f"sellers/{user_id}/{filename}"
    try:
        if is_image_ext(file.filename):
            return upload_to_storage(file, 'seller-documents', storage_path,
                                     max_width=2000, max_height=2000, quality=88)
        return upload_raw_to_storage(file, 'seller-documents', storage_path)
    except Exception as e:
        print(f'[save_seller_file] upload failed: {e}')
        return None

def save_rider_file(file, user_id, file_type):
    """Upload a rider registration document to Supabase Storage; return public URL or None."""
    if not file or file.filename == '':
        return None
    if not _allowed_doc(file.filename):
        return None
    from app.extensions import supabase_admin
    from app.utils.images import upload_to_storage, upload_raw_to_storage, is_image_ext
    ext          = file.filename.rsplit('.', 1)[1].lower()
    filename     = secure_filename(f"{file_type}_{user_id}.{ext}")
    storage_path = f"riders/{user_id}/{filename}"
    try:
        if is_image_ext(file.filename):
            return upload_to_storage(file, 'rider-documents', storage_path,
                                     max_width=2000, max_height=2000, quality=88)
        return upload_raw_to_storage(file, 'rider-documents', storage_path)
    except Exception as e:
        print(f'[save_rider_file] upload failed: {e}')
        return None

auth_bp = Blueprint('auth', __name__)

_TWO_FACTOR_PENDING_KEYS = (
    'two_factor_pending_user_id',
    'two_factor_pending_at',
)


def _clear_pending_two_factor_login():
    for key in _TWO_FACTOR_PENDING_KEYS:
        session.pop(key, None)


def _redirect_after_login(profile):
    # Merge guest/session cart with the buyer's persisted DB cart after all
    # authentication checks have passed.
    if profile.role == 'buyer':
        try:
            from app.routes.buyer.cart import _db_load, _db_sync
            session_cart = session.get('cart') or {}
            db_cart = _db_load(profile.id)
            merged = {**db_cart, **session_cart}
            session['cart'] = merged
            session.modified = True
            if merged != db_cart:
                _db_sync(profile.id, merged)
        except Exception as cart_error:
            print(f'[auth] cart restore error: {cart_error}')

    flash(
        f'Welcome back, {profile.first_name}! 👋||'
        'You have successfully logged in to KidZora.',
        'auth_popup'
    )

    role_dashboards = {
        'admin': 'admin.dashboard',
        'seller': 'seller.dashboard',
        'rider': 'rider.dashboard',
    }
    return redirect(url_for(role_dashboards.get(profile.role, 'index')))


def _two_factor_profile_row(user_id):
    result = supabase_admin.table('profiles').select('*').eq('id', user_id).execute()
    return result.data[0] if result.data else None


def _two_factor_is_enabled(profile_data):
    return bool(profile_data.get('two_factor_enabled') and profile_data.get('two_factor_secret'))


def send_confirmation_email(email, confirmation_code):
    """Send verification code email via SMTP."""
    try:
        smtp_server   = current_app.config.get('MAIL_SERVER', 'smtp.gmail.com')
        smtp_port     = int(current_app.config.get('MAIL_PORT', 465))
        username      = current_app.config.get('MAIL_USERNAME', '')
        password      = current_app.config.get('MAIL_PASSWORD', '')
        sender_full   = current_app.config.get('MAIL_DEFAULT_SENDER', username)
        use_ssl       = current_app.config.get('MAIL_USE_SSL', True)
        use_tls       = current_app.config.get('MAIL_USE_TLS', False)

        msg = MIMEMultipart('alternative')
        msg['From']    = sender_full
        msg['To']      = email
        msg['Subject'] = 'KidZora - Email Verification Code'

        html_body = f"""
        <html>
        <body style="font-family:Arial,sans-serif;background:#f4f6f9;padding:30px;">
          <div style="max-width:480px;margin:auto;background:#fff;border-radius:10px;padding:40px;box-shadow:0 2px 8px rgba(0,0,0,.1);">
            <div style="text-align:center;margin-bottom:24px;">
              <h1 style="color:#4f46e5;margin:0;">KidZora</h1>
            </div>
            <h2 style="color:#1f2937;">Verify Your Email</h2>
            <p style="color:#4b5563;">Thank you for signing up! Use the code below to verify your email address.</p>
            <div style="text-align:center;margin:32px 0;">
              <span style="font-size:36px;font-weight:bold;letter-spacing:8px;color:#4f46e5;background:#eef2ff;padding:16px 28px;border-radius:8px;">{confirmation_code}</span>
            </div>
            <p style="color:#6b7280;font-size:14px;">This code expires in <strong>10 minutes</strong>. If you didn't request this, you can safely ignore this email.</p>
            <hr style="margin:24px 0;border:none;border-top:1px solid #e5e7eb;">
            <p style="color:#9ca3af;font-size:12px;text-align:center;">The KidZora Team</p>
          </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(html_body, 'html'))

        context = ssl.create_default_context()
        if use_ssl:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port, context=context)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port)
            if use_tls:
                server.starttls(context=context)

        server.login(username, password)
        server.sendmail(username, email, msg.as_string())
        server.quit()
        print(f"Email sent via {smtp_server} to {email}")
        return True

    except smtplib.SMTPAuthenticationError as e:
        print(f"SMTP Auth Error: {e}")
        return False
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        print(f"Login attempt: {email}")

        if not supabase:
            missing = [
                name for name in ('SUPABASE_URL', 'SUPABASE_ANON_KEY')
                if not current_app.config.get(name)
            ]
            detail = ', '.join(missing) if missing else 'Supabase client initialization failed'
            current_app.logger.error('Login unavailable: %s', detail)
            flash(
                'Login service is not configured. Check the Supabase environment variables for this app.',
                'error'
            )
            return render_template('auth/login.html')
        
        try:
            # Authenticate with Supabase
            auth_response = supabase.auth.sign_in_with_password({
                'email': email,
                'password': password
            })
            
            print(f"Auth response: {auth_response}")
            
            if auth_response.user:
                print(f"User authenticated: {auth_response.user.id}")
                
                # Get user profile
                profile_result = supabase.table('profiles').select('*').eq('id', auth_response.user.id).execute()
                if profile_result.data:
                    profile_data = profile_result.data[0]
                    # Create Profile object from data
                    profile = Profile(profile_data)
                    print(f"Profile found: {profile}")
                    print(f"Profile role: {profile.role}")
                else:
                    print(f"No profile found for user ID: {auth_response.user.id}")
                    profile = None
                
                if profile:
                    print(f"Profile role: {profile.role}")

                    # Block banned users — send them to the appeal page
                    if profile_data.get('is_banned'):
                        supabase.auth.sign_out()
                        session['banned_user_id']  = profile.id
                        session['banned_user_name'] = profile.get_full_name()
                        session['ban_reason']      = profile_data.get('ban_reason', '')
                        return redirect(url_for('auth.banned_page'))

                    # Block unapproved sellers and riders
                    if profile.role in ('seller', 'rider') and not profile_data.get('is_approved'):
                        rejection_reason = profile_data.get('rejection_reason')
                        # Rejected riders may log in to re-upload documents
                        if profile.role == 'rider' and rejection_reason:
                            login_user(profile)
                            flash(
                                'Documents Rejected|'
                                f'|Your documents were rejected: {rejection_reason}. '
                                'Please re-upload your documents below.',
                                'danger'
                            )
                            return redirect(url_for('rider.profile'))
                        supabase.auth.sign_out()
                        flash('Pending Approval||Your account is under review. We will notify you by email once it is approved.', 'warning')
                        return render_template('auth/login.html')

                    if _two_factor_is_enabled(profile_data):
                        session['two_factor_pending_user_id'] = profile.id
                        session['two_factor_pending_at'] = datetime.now().isoformat()
                        try:
                            supabase.auth.sign_out()
                        except Exception:
                            pass
                        flash('Enter the code from your authenticator app to finish logging in.', 'info')
                        return redirect(url_for('auth.two_factor_verify'))

                    login_user(profile)

                    # ── GUEST CART MERGE ──────────────────────────────────────
                    # Merge guest/session cart with logged-in user's persisted DB cart.
                    # Scenarios:
                    #   1. Guest browsed + added items, then logs in → session cart merged with DB cart
                    #   2. User logged out from another device → DB cart restored (session empty)
                    #   3. User's session expired → DB cart restored (session cleared)
                    # Priority: session items take precedence (most recent user actions)
                    if profile.role == 'buyer':
                        try:
                            from app.routes.buyer.cart import _db_load, _db_sync
                            session_cart = session.get('cart') or {}  # Guest's accumulated items or empty
                            db_cart      = _db_load(profile.id)       # User's persisted cart from DB
                            merged       = {**db_cart, **session_cart}  # Session items override DB items
                            session['cart'] = merged
                            session.modified = True
                            # Persist the merged cart to DB if different from DB version
                            if merged != db_cart:
                                _db_sync(profile.id, merged)
                        except Exception as _ce:
                            print(f'[auth] cart restore error: {_ce}')

                    flash(f'Welcome back, {profile.first_name}! 👋||You have successfully logged in to KidZora.', 'auth_popup')

                    # Redirect based on role
                    if profile.role == 'admin':
                        return redirect(url_for('admin.dashboard'))
                    elif profile.role == 'seller':
                        return redirect(url_for('seller.dashboard'))
                    elif profile.role == 'buyer':
                        return redirect(url_for('index'))
                    elif profile.role == 'rider':
                        return redirect(url_for('rider.dashboard'))
                    else:
                        return redirect(url_for('index'))
                else:
                    print("Profile not found!")
                    flash('Profile not found. Please contact support.', 'error')
            else:
                print("No user in auth response")
                flash('Invalid email or password', 'error')
                
        except Exception as e:
            print(f"Login error: {e}")
            flash(f'Login failed: {str(e)}', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    _clear_pending_two_factor_login()
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    flash('Logged out successfully 👋||See you next time on KidZora!', 'auth_popup')
    return redirect(url_for('auth.login'))

@auth_bp.route('/two-factor/verify', methods=['GET', 'POST'])
def two_factor_verify():
    """Finish login for accounts that enabled authenticator-app 2FA."""
    pending_user_id = session.get('two_factor_pending_user_id')
    pending_at = session.get('two_factor_pending_at')
    if not pending_user_id or not pending_at:
        flash('Start with your email and password before entering a 2FA code.', 'info')
        return redirect(url_for('auth.login'))

    try:
        if datetime.now() - datetime.fromisoformat(pending_at) > timedelta(minutes=5):
            _clear_pending_two_factor_login()
            flash('Your 2FA login check expired. Please log in again.', 'error')
            return redirect(url_for('auth.login'))
        profile_data = _two_factor_profile_row(pending_user_id)
    except Exception as e:
        current_app.logger.exception('Could not load 2FA login profile: %s', e)
        flash('Could not verify your login right now. Please try again.', 'error')
        return redirect(url_for('auth.login'))

    if not profile_data or not _two_factor_is_enabled(profile_data):
        _clear_pending_two_factor_login()
        flash('Two-factor authentication is not available for this account.', 'error')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        secret = decrypt_secret(profile_data.get('two_factor_secret'))
        if not verify_totp(secret, request.form.get('code', '')):
            flash('That authenticator code is not valid. Try the current six-digit code.', 'error')
            return render_template('auth/two_factor_verify.html')

        if profile_data.get('is_banned'):
            _clear_pending_two_factor_login()
            flash('This account is currently banned.', 'error')
            return redirect(url_for('auth.login'))

        profile = Profile(profile_data)
        _clear_pending_two_factor_login()
        login_user(profile)
        return _redirect_after_login(profile)

    return render_template('auth/two_factor_verify.html')


@auth_bp.route('/two-factor/setup', methods=['GET', 'POST'])
@login_required
def two_factor_setup():
    """Enroll the current user in authenticator-app TOTP 2FA."""
    if not supabase_admin:
        flash('Two-factor setup is not configured right now.', 'error')
        return redirect(url_for('index'))

    try:
        profile_data = _two_factor_profile_row(current_user.id)
    except Exception as e:
        current_app.logger.exception('Could not load 2FA setup profile: %s', e)
        flash('Could not load two-factor settings.', 'error')
        return redirect(url_for('index'))

    if not profile_data:
        flash('Profile not found.', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST' and not _two_factor_is_enabled(profile_data):
        pending_secret = decrypt_secret(session.get('two_factor_setup_secret'))
        if not verify_totp(pending_secret, request.form.get('code', '')):
            flash('Enter the current six-digit code from your authenticator app.', 'error')
            return redirect(url_for('auth.two_factor_setup'))

        try:
            supabase_admin.table('profiles').update({
                'two_factor_enabled': True,
                'two_factor_secret': encrypt_secret(pending_secret),
                'two_factor_confirmed_at': datetime.utcnow().isoformat(),
            }).eq('id', current_user.id).execute()
        except Exception as e:
            current_app.logger.exception('Could not enable 2FA: %s', e)
            flash('Could not enable 2FA. Run the two-factor profile migration and try again.', 'error')
            return redirect(url_for('auth.two_factor_setup'))

        session.pop('two_factor_setup_secret', None)
        flash('Authenticator two-factor authentication is enabled.', 'success')
        return redirect(url_for('auth.two_factor_setup'))

    if _two_factor_is_enabled(profile_data):
        session.pop('two_factor_setup_secret', None)
        return render_template('auth/two_factor_setup.html', two_factor_enabled=True)

    setup_secret = decrypt_secret(session.get('two_factor_setup_secret'))
    if not setup_secret:
        setup_secret = new_totp_secret()
        session['two_factor_setup_secret'] = encrypt_secret(setup_secret)

    uri = provisioning_uri(current_user.email, setup_secret)
    return render_template(
        'auth/two_factor_setup.html',
        two_factor_enabled=False,
        manual_secret=setup_secret,
        qr_code=qr_data_uri(uri),
        provisioning_uri=uri,
    )


@auth_bp.route('/two-factor/disable', methods=['POST'])
@login_required
def two_factor_disable():
    """Disable authenticator-app TOTP after a valid current code."""
    try:
        profile_data = _two_factor_profile_row(current_user.id)
    except Exception as e:
        current_app.logger.exception('Could not load 2FA disable profile: %s', e)
        flash('Could not load two-factor settings.', 'error')
        return redirect(url_for('auth.two_factor_setup'))

    secret = decrypt_secret((profile_data or {}).get('two_factor_secret'))
    if not _two_factor_is_enabled(profile_data or {}):
        flash('Two-factor authentication is already disabled.', 'info')
        return redirect(url_for('auth.two_factor_setup'))
    if not verify_totp(secret, request.form.get('code', '')):
        flash('Enter a valid current authenticator code to disable 2FA.', 'error')
        return redirect(url_for('auth.two_factor_setup'))

    try:
        supabase_admin.table('profiles').update({
            'two_factor_enabled': False,
            'two_factor_secret': None,
            'two_factor_confirmed_at': None,
        }).eq('id', current_user.id).execute()
    except Exception as e:
        current_app.logger.exception('Could not disable 2FA: %s', e)
        flash('Could not disable 2FA right now.', 'error')
        return redirect(url_for('auth.two_factor_setup'))

    flash('Authenticator two-factor authentication is disabled.', 'success')
    return redirect(url_for('auth.two_factor_setup'))


@auth_bp.route('/banned')
def banned_page():
    """Shown when a banned user tries to log in."""
    user_id   = session.get('banned_user_id')
    if not user_id:
        return redirect(url_for('auth.login'))
    ban_reason  = session.get('ban_reason', '')
    user_name   = session.get('banned_user_name', 'User')
    # Check if there's already a pending appeal
    has_pending = False
    try:
        r = supabase_admin.table('unban_requests') \
            .select('id').eq('user_id', user_id).eq('status', 'pending').execute()
        has_pending = bool(r.data)
    except Exception:
        pass
    return render_template('auth/banned.html',
                           ban_reason=ban_reason,
                           user_name=user_name,
                           has_pending=has_pending)


@auth_bp.route('/appeal', methods=['POST'])
def submit_appeal():
    """Submit an unban appeal request."""
    user_id = session.get('banned_user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    message = request.form.get('message', '').strip()
    if not message:
        flash('Please describe your appeal.', 'error')
        return redirect(url_for('auth.banned_page'))

    # Save uploaded file if provided
    file_url = None
    file = request.files.get('document')
    if file and file.filename and _allowed_doc(file.filename):
        from app.utils.images import upload_to_storage, upload_raw_to_storage, is_image_ext
        ext          = file.filename.rsplit('.', 1)[1].lower()
        filename     = secure_filename(f"{user_id}_{file.filename}")
        storage_path = f"appeals/{user_id}/{filename}"
        try:
            if is_image_ext(file.filename):
                file_url = upload_to_storage(file, 'appeals', storage_path,
                                             max_width=2000, max_height=2000, quality=88)
            else:
                file_url = upload_raw_to_storage(file, 'appeals', storage_path)
        except Exception as e:
            print(f'[appeal upload] failed: {e}')

    # Cancel any previous pending requests first
    try:
        supabase_admin.table('unban_requests') \
            .update({'status': 'superseded'}) \
            .eq('user_id', user_id).eq('status', 'pending').execute()
    except Exception:
        pass

    # Insert the new appeal
    try:
        supabase_admin.table('unban_requests').insert({
            'user_id':  user_id,
            'message':  message,
            'file_url': file_url,
            'status':   'pending',
        }).execute()
    except Exception as e:
        print(f'appeal insert error: {e}')
        flash('Could not submit appeal. Please try again.', 'error')
        return redirect(url_for('auth.banned_page'))

    session.pop('banned_user_id', None)
    session.pop('ban_reason', None)
    session.pop('banned_user_name', None)
    flash('Appeal Submitted||We will review your request and notify you by email shortly.', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/email-verification', methods=['GET'])
def email_verification():
    """Email verification page"""
    return render_template('auth/email_verification.html')

@auth_bp.route('/send-confirmation-code', methods=['POST'])
def send_confirmation_code():
    """Send confirmation code to email"""
    email = request.form.get('email')
    
    if not email:
        flash('Please enter your email address', 'error')
        return redirect(url_for('auth.email_verification'))
    
    # Generate 6-digit confirmation code
    confirmation_code = ''.join(random.choices(string.digits, k=6))
    
    # Store in session (in production, use database with expiry)
    session['verification_email'] = email
    session['confirmation_code'] = confirmation_code
    session['code_generated_at'] = datetime.now().isoformat()
    
    # Send confirmation email
    email_sent = send_confirmation_email(email, confirmation_code)
    
    if email_sent:
        flash(f'Confirmation code sent to {email}', 'info')
    else:
        flash('Failed to send confirmation code. Please try again.', 'error')
        flash(f'For testing: {confirmation_code}', 'info')  # Show code for testing
    
    return redirect(url_for('auth.email_verification'))

@auth_bp.route('/verify-code', methods=['POST'])
def verify_code():
    """Verify confirmation code"""
    email = session.get('verification_email')
    stored_code = session.get('confirmation_code')
    code_generated_at = session.get('code_generated_at')
    
    if not email or not stored_code:
        flash('Session expired. Please request a new confirmation code.', 'error')
        return redirect(url_for('auth.email_verification'))
    
    # Check if code is expired (10 minutes)
    if code_generated_at:
        generated_time = datetime.fromisoformat(code_generated_at)
        if datetime.now() - generated_time > timedelta(minutes=10):
            flash('Confirmation code expired. Please request a new one.', 'error')
            return redirect(url_for('auth.email_verification'))
    
    submitted_code = request.form.get('confirmation_code')
    
    if submitted_code == stored_code:
        # Code is correct, clear session and redirect to registration
        session.pop('confirmation_code', None)
        session.pop('code_generated_at', None)
        session['email_verified'] = True
        session['verified_email'] = email
        
        flash('Email Verified!||Your email has been confirmed. Please complete your registration.', 'success')
        return redirect(url_for('auth.register'))
    else:
        flash('Invalid confirmation code. Please try again.', 'error')
        return redirect(url_for('auth.email_verification'))

@auth_bp.route('/resend-code', methods=['POST'])
def resend_code():
    """Resend confirmation code"""
    data = request.get_json()
    email = data.get('email')
    
    if not email:
        return jsonify({'success': False, 'message': 'Email required'})
    
    # Generate new code
    confirmation_code = ''.join(random.choices(string.digits, k=6))
    
    # Update session
    session['confirmation_code'] = confirmation_code
    session['code_generated_at'] = datetime.now().isoformat()
    
    # Send confirmation email
    email_sent = send_confirmation_email(email, confirmation_code)
    
    if email_sent:
        return jsonify({'success': True, 'message': 'Code resent successfully'})
    else:
        return jsonify({'success': False, 'message': 'Failed to send email'})

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Single page registration with email verification"""
    if request.method == 'GET':
        return render_template('auth/register_single.html')
    
    if request.method == 'POST':
        # Check if this is email verification step
        if request.form.get('email_verified') == 'true':
            # Email verified, proceed with full registration
            email = request.form.get('email')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            phone = request.form.get('phone')
            role = request.form.get('role')
            newsletter = request.form.get('newsletter')
            terms = request.form.get('terms')
            privacy = request.form.get('privacy')
            
            # Address fields
            building_number = request.form.get('building_number')
            street_name = request.form.get('street_name')
            city = request.form.get('city')
            postal_code = request.form.get('postal_code')
            country = request.form.get('country', 'Philippines')
            region = request.form.get('region')
            province = request.form.get('province')
            barangay = request.form.get('barangay')
            
            # Seller-specific fields
            business_name = request.form.get('business_name')
            business_type = request.form.get('business_type')
            seller_id_type = request.form.get('seller_id_type')
            seller_id_number = request.form.get('seller_id_number')
            seller_id_file = request.files.get('seller_id_file')
            business_permit_file = request.files.get('business_permit_file')
            bir_file = request.files.get('bir_file')

            # Rider-specific fields
            rider_licensed_id_file = request.files.get('licensed_id')
            rider_receipt_file = request.files.get('original_receipt')
            rider_cor_file = request.files.get('certificate_of_registration')
            
            # Validation
            if not email or not password or not first_name or not last_name or not phone or not role:
                flash('Please fill in all required fields.', 'error')
                return jsonify({'success': False, 'message': 'Missing required fields'})
            
            if password != confirm_password:
                flash('Passwords do not match.', 'error')
                return jsonify({'success': False, 'message': 'Passwords do not match'})
            
            if not terms or not privacy:
                flash('You must agree to Terms and Conditions and Privacy Policy.', 'error')
                return jsonify({'success': False, 'message': 'Must agree to terms and privacy'})
            
            # Validate address fields
            if not building_number or not street_name:
                flash('Please enter both building number and street name.', 'error')
                return jsonify({'success': False, 'message': 'Missing address fields'})
            
            # Validate location fields
            if not region or not province or not city or not barangay:
                flash('Please complete all location fields.', 'error')
                return jsonify({'success': False, 'message': 'Missing location fields'})

            # Validate phone — exactly 11 digits, numbers only
            if not re.fullmatch(r'[0-9]{11}', phone or ''):
                return jsonify({'success': False, 'message': 'Phone number must be exactly 11 digits with no letters.'})

            # Validate postal code — exactly 4 digits
            if not re.fullmatch(r'[0-9]{4}', postal_code or ''):
                return jsonify({'success': False, 'message': 'Postal code must be exactly 4 digits.'})
            
            # Validate seller-specific fields if seller
            if role == 'seller':
                if not business_name or not business_type or not seller_id_type or not seller_id_number:
                    flash('Please complete all seller business information fields.', 'error')
                    return jsonify({'success': False, 'message': 'Missing seller information'})


            
            try:
                supabase_url = current_app.config.get('SUPABASE_URL')
                service_key  = current_app.config.get('SUPABASE_SERVICE_ROLE_KEY')

                # --- Case 1: orphaned profile row (profile exists, auth may be gone) ---
                # Happens when user was deleted from Auth but profiles row was not removed.
                existing_profile = supabase.table('profiles').select('id').eq('email', email).execute()
                if existing_profile.data:
                    orphan_id = existing_profile.data[0]['id']
                    check_resp = http_requests.get(
                        f"{supabase_url}/auth/v1/admin/users/{orphan_id}",
                        headers={'apikey': service_key, 'Authorization': f'Bearer {service_key}'},
                        timeout=10
                    )
                    if check_resp.status_code == 404:
                        # Auth user gone — remove the stale profile row
                        supabase.table('profiles').delete().eq('id', orphan_id).execute()
                        print(f"Removed orphaned profile row for {email}")
                    else:
                        # Auth user still exists with a valid profile — genuinely taken
                        return jsonify({'success': False, 'message': 'An account with this email already exists. Please log in or use a different email.'})

                # --- Case 2: orphaned auth user (no profile, but auth account exists) ---
                # Happens when admin rejected the user — profile was deleted but auth was not.
                else:
                    search_resp = http_requests.get(
                        f"{supabase_url}/auth/v1/admin/users",
                        headers={'apikey': service_key, 'Authorization': f'Bearer {service_key}'},
                        params={'email': email, 'page': 1, 'per_page': 1},
                        timeout=10
                    )
                    if search_resp.status_code == 200:
                        found_users = search_resp.json().get('users', [])
                        if found_users:
                            orphan_auth_id = found_users[0].get('id')
                            # No profile row means this user was rejected — safe to purge
                            del_resp = http_requests.delete(
                                f"{supabase_url}/auth/v1/admin/users/{orphan_auth_id}",
                                headers={'apikey': service_key, 'Authorization': f'Bearer {service_key}'},
                                timeout=10
                            )
                            if del_resp.status_code in (200, 204):
                                print(f"Removed orphaned auth user for {email} (was previously rejected)")
                            else:
                                print(f"Could not delete orphaned auth user: {del_resp.text}")

                create_resp = http_requests.post(
                    f"{supabase_url}/auth/v1/admin/users",
                    headers={
                        'apikey': service_key,
                        'Authorization': f'Bearer {service_key}',
                        'Content-Type': 'application/json'
                    },
                    json={
                        'email': email,
                        'password': password,
                        'email_confirm': True,
                        'user_metadata': {
                            'first_name': first_name,
                            'last_name': last_name,
                            'phone': phone
                        }
                    },
                    timeout=10
                )

                if create_resp.status_code not in (200, 201):
                    err_body = create_resp.json()
                    err_msg  = err_body.get('message', create_resp.text)
                    # Duplicate email in Auth (shouldn't happen after pre-check, but guard anyway)
                    if 'already registered' in err_msg.lower() or 'already exists' in err_msg.lower() or '23505' in str(err_body):
                        return jsonify({'success': False, 'message': 'An account with this email already exists. Please log in or use a different email.'})
                    print(f"Supabase create_user error: {err_msg}")
                    return jsonify({'success': False, 'message': f'Registration failed: {err_msg}'})

                user_data = create_resp.json()
                user_id = user_data.get('id')

                # Fake auth_response-like object so the rest of the code works
                class _User:
                    def __init__(self, uid): self.id = uid
                class _Resp:
                    def __init__(self, uid): self.user = _User(uid)
                auth_response = _Resp(user_id)
                
                if auth_response.user:
                    # Create profile with all fields
                    profile_data = {
                        'id': auth_response.user.id,
                        'email': email,
                        'first_name': first_name,
                        'last_name': last_name,
                        'phone': phone,
                        'role': role,
                        'is_approved': role == 'buyer',  # Auto-approve buyers
                        'building_number': building_number,
                        'street_name': street_name,
                        'city': city,
                        'postal_code': postal_code,
                        'country': country,
                        'region': region,
                        'province': province,
                        'barangay': barangay,
                        'newsletter': newsletter == 'on'
                    }
                    
                    # Add seller-specific fields if role is seller
                    if role == 'seller':
                        # Save uploaded documents
                        seller_id_file_url    = save_seller_file(seller_id_file,       auth_response.user.id, 'gov_id')
                        biz_permit_file_url   = save_seller_file(business_permit_file,  auth_response.user.id, 'business_permit')
                        bir_cert_file_url     = save_seller_file(bir_file,              auth_response.user.id, 'bir_cert')
                        profile_data.update({
                            'business_name':       business_name,
                            'business_type':       business_type,
                            'seller_id_type':      seller_id_type,
                            'seller_id_number':    seller_id_number,
                            'seller_id_file':      seller_id_file_url,
                            'business_permit_file': biz_permit_file_url,
                            'bir_file':            bir_cert_file_url,
                            'is_approved': False  # Sellers need admin approval
                        })
                    
                    profile = Profile.create(profile_data)
                    if profile:
                        # Create sellers row so products can reference sellers.id
                        if role == 'seller':
                            try:
                                supabase_admin.table('sellers').insert({
                                    'user_id':    auth_response.user.id,
                                    'shop_name':  business_name or 'My Shop',
                                }).execute()
                            except Exception as se:
                                print(f"Warning: could not create sellers row: {se}")

                        # Create riders row + rider_documents
                        if role == 'rider':
                            try:
                                rider_row = supabase_admin.table('riders').insert({
                                    'user_id': auth_response.user.id,
                                }).execute()
                            except Exception as re_:
                                print(f"Warning: could not create riders row: {re_}")

                            try:
                                licensed_id_url = save_rider_file(rider_licensed_id_file, auth_response.user.id, 'licensed_id')
                                receipt_url     = save_rider_file(rider_receipt_file,      auth_response.user.id, 'original_receipt')
                                cor_url         = save_rider_file(rider_cor_file,          auth_response.user.id, 'cor')
                                supabase_admin.table('riders').update({
                                    'licensed_id_url':                licensed_id_url,
                                    'original_receipt_url':           receipt_url,
                                    'certificate_of_registration_url': cor_url,
                                }).eq('user_id', auth_response.user.id).execute()
                            except Exception as rd_:
                                print(f"Warning: could not save rider documents: {rd_}")

                        flash('Registration Complete!||Your account has been created. Please log in to continue.', 'success')
                        return jsonify({'success': True, 'message': 'Account created successfully'})
                    else:
                        flash('Registration failed. Please try again.', 'error')
                        return jsonify({'success': False, 'message': 'Failed to create profile'})
                else:
                    flash('Registration failed. Please try again.', 'error')
                    return jsonify({'success': False, 'message': 'Failed to create user'})
                    
            except Exception as e:
                print(f"Registration error: {str(e)}")
                print(f"Error type: {type(e)}")
                flash(f'Registration failed: {str(e)}', 'error')
                return jsonify({'success': False, 'message': str(e)})
        
        else:
            # Initial form submission - send confirmation code
            email = request.form.get('email')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            
            # Basic validation
            if not email or not password or not confirm_password:
                flash('Please fill in all required fields.', 'error')
                return jsonify({'success': False, 'message': 'Missing required fields'})
            
            # Password validation
            password_pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])(?=.*[!@#$%^&*()_+\-=\[\]{};:\'"|<>?,./`~]).{8,}$'
            if not re.match(password_pattern, password):
                flash('Password must contain at least one lowercase letter, one uppercase letter, one number, one special character, and be at least 8 characters long.', 'error')
                return jsonify({'success': False, 'message': 'Password does not meet requirements'})
            
            if password != confirm_password:
                flash('Passwords do not match.', 'error')
                return jsonify({'success': False, 'message': 'Passwords do not match'})
            
            try:
                # Generate 6-digit confirmation code
                confirmation_code = ''.join(random.choices(string.digits, k=6))
                
                # Store in session
                session['registration_email'] = email
                session['registration_password'] = password
                session['registration_data'] = {
                    'first_name': request.form.get('first_name'),
                    'last_name': request.form.get('last_name'),
                    'phone': request.form.get('phone'),
                    'role': request.form.get('role'),
                    'newsletter': request.form.get('newsletter'),
                    'terms': request.form.get('terms'),
                    'privacy': request.form.get('privacy'),
                    'building_number': request.form.get('building_number'),
                    'street_name': request.form.get('street_name'),
                    'city': request.form.get('city'),
                    'postal_code': request.form.get('postal_code'),
                    'country': request.form.get('country', 'Philippines'),
                    'region': request.form.get('region'),
                    'province': request.form.get('province'),
                    'barangay': request.form.get('barangay'),
                    'business_name': request.form.get('business_name'),
                    'business_type': request.form.get('business_type'),
                    'seller_id_type': request.form.get('seller_id_type'),
                    'seller_id_number': request.form.get('seller_id_number')
                }
                session['confirmation_code'] = confirmation_code
                session['code_generated_at'] = datetime.now().isoformat()
                
                # Send confirmation email
                email_sent = send_confirmation_email(email, confirmation_code)
                
                if email_sent:
                    return jsonify({'success': True, 'message': 'Confirmation code sent to your email.'})
                else:
                    return jsonify({'success': False, 'message': 'Failed to send verification email. Please check your email address and try again.'})
                    
            except Exception as e:
                print(f"Error sending confirmation code: {str(e)}")
                return jsonify({'success': False, 'message': f'Server error: {str(e)}'})

@auth_bp.route('/api/verify-code', methods=['POST'])
def api_verify_code():
    """JSON endpoint: verify the confirmation code sent during registration."""
    data = request.get_json(silent=True) or {}
    email = data.get('email') or request.form.get('email')
    submitted_code = data.get('confirmation_code') or request.form.get('confirmation_code')

    stored_code = session.get('confirmation_code')
    stored_email = session.get('registration_email')
    code_generated_at = session.get('code_generated_at')

    if not stored_code or not stored_email:
        return jsonify({'success': False, 'message': 'Session expired. Please request a new code.'})

    # Check expiry (10 minutes)
    if code_generated_at:
        generated_time = datetime.fromisoformat(code_generated_at)
        if datetime.now() - generated_time > timedelta(minutes=10):
            session.pop('confirmation_code', None)
            session.pop('code_generated_at', None)
            return jsonify({'success': False, 'message': 'Code expired. Please request a new one.'})

    if submitted_code == stored_code:
        session.pop('confirmation_code', None)
        session.pop('code_generated_at', None)
        return jsonify({'success': True, 'message': 'Email verified successfully.'})
    else:
        return jsonify({'success': False, 'message': 'Invalid code. Please try again.'})


@auth_bp.route('/dashboard')
@login_required
def dashboard():
    return redirect(url_for('buyer.dashboard'))


# ── Forgot Password ────────────────────────────────────────────────────────────

@auth_bp.route('/forgot-password', methods=['GET'])
def forgot_password():
    """Forgot password page — 3-step: email → OTP → new password."""
    return render_template('auth/forgot_password.html')


@auth_bp.route('/forgot-password/send-code', methods=['POST'])
def forgot_password_send_code():
    """Step 1 — Send OTP to the submitted email if it exists."""
    data  = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()

    if not email:
        return jsonify({'success': False, 'message': 'Email is required.'})

    # Use service-role client for backend lookup (RLS-safe and consistent).
    try:
        if not supabase_admin:
            print('[forgot_password_send_code] supabase_admin is not configured')
            return jsonify({'success': False, 'message': 'Service is temporarily unavailable. Please try again in a moment.'})

        result = supabase_admin.table('profiles').select('id, first_name, role').eq('email', email).execute()
    except Exception as e:
        err = str(e)
        print(f'[forgot_password_send_code] profile lookup error: {err}')
        if 'getaddrinfo failed' in err.lower():
            return jsonify({
                'success': False,
                'message': 'Cannot reach the database service right now (DNS/network issue). Please check server internet/DNS and try again.'
            })
        return jsonify({'success': False, 'message': 'Could not verify this email right now. Please try again.'})

    if not result.data:
        # Don't reveal whether email exists — generic message
        return jsonify({'success': True, 'message': 'If that email is registered, a code has been sent.'})

    user = result.data[0]

    # Generate 6-digit OTP
    code = ''.join(random.choices(string.digits, k=6))
    session['fp_email']        = email
    session['fp_user_id']      = user['id']
    session['fp_code']         = code
    session['fp_generated_at'] = datetime.now().isoformat()
    session['fp_verified']     = False

    # Send email
    try:
        smtp_server = current_app.config.get('MAIL_SERVER', 'smtp.gmail.com')
        smtp_port   = int(current_app.config.get('MAIL_PORT', 465))
        username    = current_app.config.get('MAIL_USERNAME', '')
        password    = current_app.config.get('MAIL_PASSWORD', '')
        use_ssl     = current_app.config.get('MAIL_USE_SSL', True)
        use_tls     = current_app.config.get('MAIL_USE_TLS', False)
        sender_full = current_app.config.get('MAIL_DEFAULT_SENDER', username)

        msg = MIMEMultipart('alternative')
        msg['From']    = sender_full
        msg['To']      = email
        msg['Subject'] = 'KidZora – Password Reset Code'

        html = f"""
        <html>
        <body style="font-family:Arial,sans-serif;background:#f4f6f9;padding:30px;">
          <div style="max-width:480px;margin:auto;background:#fff;border-radius:10px;padding:40px;box-shadow:0 2px 8px rgba(0,0,0,.1);">
            <div style="text-align:center;margin-bottom:24px;">
              <h1 style="color:#4f46e5;margin:0;">KidZora</h1>
            </div>
            <h2 style="color:#1f2937;">Password Reset</h2>
            <p style="color:#4b5563;">Hi {user.get('first_name', '')}! Use the code below to reset your password.</p>
            <div style="text-align:center;margin:32px 0;">
              <span style="font-size:36px;font-weight:bold;letter-spacing:8px;color:#4f46e5;background:#eef2ff;padding:16px 28px;border-radius:8px;">{code}</span>
            </div>
            <p style="color:#6b7280;font-size:14px;">This code expires in <strong>10 minutes</strong>. If you did not request a password reset, you can safely ignore this email.</p>
            <hr style="margin:24px 0;border:none;border-top:1px solid #e5e7eb;">
            <p style="color:#9ca3af;font-size:12px;text-align:center;">The KidZora Team</p>
          </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(html, 'html'))

        context = ssl.create_default_context()
        if use_ssl:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port, context=context)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port)
            if use_tls:
                server.starttls(context=context)
        server.login(username, password)
        server.sendmail(username, email, msg.as_string())
        server.quit()
    except Exception as e:
        err = str(e)
        print(f"forgot password email error: {err}")
        if 'getaddrinfo failed' in err.lower():
            return jsonify({
                'success': False,
                'message': 'Cannot reach the email server right now (DNS/network issue). Please verify MAIL_SERVER and server internet, then try again.'
            })
        return jsonify({'success': False, 'message': 'Could not send email. Please try again.'})

    return jsonify({'success': True, 'message': 'Code sent! Check your inbox.'})


@auth_bp.route('/forgot-password/verify-code', methods=['POST'])
def forgot_password_verify_code():
    """Step 2 — Validate the OTP."""
    data      = request.get_json(silent=True) or {}
    submitted = (data.get('code') or '').strip()

    stored_code = session.get('fp_code')
    generated   = session.get('fp_generated_at')

    if not stored_code:
        return jsonify({'success': False, 'message': 'Session expired. Please request a new code.'})

    if generated:
        if datetime.now() - datetime.fromisoformat(generated) > timedelta(minutes=10):
            session.pop('fp_code', None)
            return jsonify({'success': False, 'message': 'Code expired. Please request a new one.'})

    if submitted != stored_code:
        return jsonify({'success': False, 'message': 'Invalid code. Please try again.'})

    session['fp_verified'] = True
    session.pop('fp_code', None)
    return jsonify({'success': True, 'message': 'Code verified!'})


@auth_bp.route('/forgot-password/reset', methods=['POST'])
def forgot_password_reset():
    """Step 3 — Set the new password."""
    if not session.get('fp_verified'):
        return jsonify({'success': False, 'message': 'Please verify your email first.'})

    data             = request.get_json(silent=True) or {}
    new_password     = data.get('password', '')
    confirm_password = data.get('confirm_password', '')

    password_pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])(?=.*[!@#$%^&*()_+\-=\[\]{};:\'"|<>?,./`~]).{8,}$'
    if not re.match(password_pattern, new_password):
        return jsonify({'success': False, 'message': 'Password must be at least 8 characters with uppercase, lowercase, number and special character.'})

    if new_password != confirm_password:
        return jsonify({'success': False, 'message': 'Passwords do not match.'})

    user_id      = session.get('fp_user_id')
    supabase_url = current_app.config.get('SUPABASE_URL')
    service_key  = current_app.config.get('SUPABASE_SERVICE_ROLE_KEY')

    try:
        resp = http_requests.put(
            f"{supabase_url}/auth/v1/admin/users/{user_id}",
            headers={
                'apikey':        service_key,
                'Authorization': f'Bearer {service_key}',
                'Content-Type':  'application/json',
            },
            json={'password': new_password},
            timeout=10,
        )
        if resp.status_code not in (200, 201):
            return jsonify({'success': False, 'message': 'Failed to update password. Please try again.'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {e}'})

    # Clear all forgot-password session keys
    for key in ('fp_email', 'fp_user_id', 'fp_code', 'fp_generated_at', 'fp_verified'):
        session.pop(key, None)

    return jsonify({'success': True, 'message': 'Password reset successfully! You can now log in.'})
