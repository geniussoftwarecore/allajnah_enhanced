from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import pyotp
import qrcode
import io
import base64
import json
import os
from datetime import datetime, timedelta
from functools import wraps
from marshmallow import ValidationError
from src.models.complaint import db, User, Role
from src.services.job_queue import enqueue_notification
from src.services.session_service import session_service
from src.utils.security import lockout_service
from src.utils.password_policy import validate_password_strength
from src.schemas.user import (
    InitialSetupSchema, UserCreateSchema, UserUpdateSchema, UserLoginSchema,
    ChangePasswordSchema, RefreshTokenSchema, RevokeSessionSchema
)

auth_bp = Blueprint('auth', __name__)

def rate_limit(limit_string):
    """Decorator wrapper for rate limiting"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                limiter = current_app.limiter
                return limiter.limit(limit_string)(f)(*args, **kwargs)
            except AttributeError:
                return f(*args, **kwargs)
        return decorated_function
    return decorator

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({'message': 'تنسيق رمز التوثيق غير صالح'}), 401
        
        if not token:
            return jsonify({'message': 'رمز التوثيق مفقود'}), 401
        
        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = User.query.filter_by(user_id=data['user_id']).first()
            if not current_user:
                return jsonify({'message': 'رمز التوثيق غير صالح'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'انتهت صلاحية رمز التوثيق'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'رمز التوثيق غير صالح'}), 401
        
        subscription_exempt_routes = [
            '/api/subscription/status',
            '/api/subscription/me',
            '/api/payment-methods',
            '/api/subscription-price',
            '/api/payment/submit',
            '/api/payment/receipt',
            '/api/payments',
            '/api/renewal/check',
            '/api/profile'
        ]
        
        if current_user.role.role_name == 'Trader':
            if not any(request.path.startswith(route) for route in subscription_exempt_routes):
                from src.models.complaint import Subscription, Settings
                
                active_subscription = Subscription.query.filter_by(
                    user_id=current_user.user_id,
                    status='active'
                ).order_by(Subscription.end_date.desc()).first()
                
                if not active_subscription:
                    return jsonify({
                        'message': 'يجب تفعيل الاشتراك للوصول إلى هذه الميزة',
                        'requires_subscription': True
                    }), 403
                
                grace_period_setting = Settings.query.filter_by(key='grace_period_days').first()
                grace_period_days = int(grace_period_setting.value) if grace_period_setting else 7
                
                enable_grace_period = Settings.query.filter_by(key='enable_grace_period').first()
                grace_enabled = enable_grace_period.value.lower() == 'true' if enable_grace_period else True
                
                if active_subscription.end_date < datetime.utcnow():
                    if grace_enabled and active_subscription.grace_period_enabled:
                        grace_end = active_subscription.end_date + timedelta(days=grace_period_days)
                        if datetime.utcnow() > grace_end:
                            return jsonify({
                                'message': 'انتهت فترة السماح. يجب تجديد الاشتراك للوصول إلى هذه الميزة',
                                'requires_subscription': True,
                                'grace_period_expired': True
                            }), 403
                    else:
                        return jsonify({
                            'message': 'انتهى الاشتراك. يجب التجديد للوصول إلى هذه الميزة',
                            'requires_subscription': True
                        }), 403
        
        return f(current_user, *args, **kwargs)
    
    return decorated

def role_required(required_roles):
    def decorator(f):
        @wraps(f)
        def decorated(current_user, *args, **kwargs):
            if current_user.role.role_name not in required_roles:
                return jsonify({'message': 'صلاحيات غير كافية'}), 403
            return f(current_user, *args, **kwargs)
        return decorated
    return decorator

def subscription_required(f):
    @wraps(f)
    def decorated(current_user, *args, **kwargs):
        if current_user.role.role_name == 'Trader':
            from src.models.complaint import Subscription
            active_subscription = Subscription.query.filter_by(
                user_id=current_user.user_id,
                status='active'
            ).filter(Subscription.end_date > datetime.utcnow()).first()
            
            if not active_subscription:
                return jsonify({
                    'message': 'يجب تفعيل الاشتراك للوصول إلى هذه الميزة',
                    'requires_subscription': True
                }), 403
        
        return f(current_user, *args, **kwargs)
    
    return decorated

@auth_bp.route('/setup/status', methods=['GET'])
def check_setup_status():
    """Check if the system needs initial setup (no admin exists)"""
    try:
        admin_role = Role.query.filter_by(role_name='Higher Committee').first()
        if not admin_role:
            return jsonify({
                'setup_required': True,
                'message': 'النظام يحتاج إلى إعداد أولي'
            }), 200
        
        admin_exists = User.query.filter_by(role_id=admin_role.role_id).first() is not None
        
        return jsonify({
            'setup_required': not admin_exists,
            'message': 'تم إعداد النظام بالفعل' if admin_exists else 'النظام يحتاج إلى إعداد أولي'
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'خطأ في التحقق من حالة الإعداد: {str(e)}'}), 500

@auth_bp.route('/setup/init', methods=['POST'])
@rate_limit("2 per hour")
def initial_setup():
    """Create the first admin account - only works if no admin exists"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'message': 'البيانات مطلوبة'}), 400
        
        schema = InitialSetupSchema()
        try:
            validated_data = schema.load(data)
        except ValidationError as err:
            return jsonify({'message': 'بيانات غير صالحة', 'errors': err.messages}), 400
        
        is_valid, errors = validate_password_strength(validated_data['password'])
        if not is_valid:
            return jsonify({'message': 'كلمة المرور ضعيفة', 'errors': errors}), 400
        
        db.session.begin_nested()
        
        admin_role = Role.query.filter_by(role_name='Higher Committee').with_for_update().first()
        if not admin_role:
            db.session.rollback()
            return jsonify({'message': 'خطأ: دور اللجنة العليا غير موجود في النظام'}), 500
        
        admin_exists = User.query.filter_by(role_id=admin_role.role_id).with_for_update().first()
        if admin_exists:
            db.session.rollback()
            return jsonify({
                'message': 'تم إعداد النظام بالفعل. لا يمكن إنشاء حساب مسؤول إضافي عبر هذه الصفحة',
                'setup_already_complete': True
            }), 403
        
        if User.query.filter_by(username=validated_data['username']).first():
            db.session.rollback()
            return jsonify({'message': 'اسم المستخدم موجود بالفعل'}), 400
        
        if User.query.filter_by(email=validated_data['email']).first():
            db.session.rollback()
            return jsonify({'message': 'البريد الإلكتروني موجود بالفعل'}), 400
        
        hashed_password = generate_password_hash(validated_data['password'])
        new_admin = User(
            username=validated_data['username'],
            email=validated_data['email'],
            password_hash=hashed_password,
            full_name=validated_data['full_name'],
            phone_number=validated_data.get('phone_number'),
            address=validated_data.get('address'),
            role_id=admin_role.role_id,
            is_active=True,
            last_password_change=datetime.utcnow()
        )
        
        db.session.add(new_admin)
        db.session.commit()
        
        return jsonify({
            'message': 'تم إنشاء حساب المسؤول بنجاح. يمكنك الآن تسجيل الدخول',
            'user': new_admin.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'خطأ في إنشاء حساب المسؤول: {str(e)}'}), 500

@auth_bp.route('/admin/create-user', methods=['POST'])
@token_required
@role_required(['Higher Committee'])
def admin_create_user(current_user):
    """Admin-only endpoint to create user accounts"""
    try:
        data = request.get_json()
        
        schema = UserCreateSchema()
        try:
            validated_data = schema.load(data)
        except ValidationError as err:
            return jsonify({'message': 'بيانات غير صالحة', 'errors': err.messages}), 400
        
        is_valid, errors = validate_password_strength(validated_data['password'])
        if not is_valid:
            return jsonify({'message': 'كلمة المرور ضعيفة', 'errors': errors}), 400
        
        allowed_roles = ['Trader', 'Technical Committee']
        role = Role.query.filter_by(role_id=validated_data['role_id']).first()
        if not role or role.role_name not in allowed_roles:
            return jsonify({'message': f'يمكن فقط إنشاء حسابات للأدوار التالية: {", ".join(allowed_roles)}'}), 400
        
        if User.query.filter_by(username=validated_data['username']).first():
            return jsonify({'message': 'اسم المستخدم موجود بالفعل'}), 400
        
        if User.query.filter_by(email=validated_data['email']).first():
            return jsonify({'message': 'البريد الإلكتروني موجود بالفعل'}), 400
        
        hashed_password = generate_password_hash(validated_data['password'])
        new_user = User(
            username=validated_data['username'],
            email=validated_data['email'],
            password_hash=hashed_password,
            full_name=validated_data['full_name'],
            phone_number=validated_data.get('phone_number'),
            address=validated_data.get('address'),
            role_id=validated_data['role_id'],
            is_active=True,
            last_password_change=datetime.utcnow()
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        enqueue_notification(
            user_id=new_user.user_id,
            notification_type='welcome',
            message=f'مرحباً بك في نظام الشكاوى الإلكتروني!',
            channel='email',
            username=new_user.username,
            email=new_user.email,
            temporary_password=validated_data['password']
        )
        
        return jsonify({
            'message': 'تم إنشاء الحساب بنجاح',
            'user': new_user.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'خطأ في إنشاء المستخدم: {str(e)}'}), 500

@auth_bp.route('/register', methods=['POST'])
@rate_limit("2 per hour")
def register():
    """Public registration is disabled"""
    return jsonify({
        'message': 'التسجيل الذاتي غير متاح. يتم إنشاء الحسابات من قبل إدارة اللجنة العليا فقط',
        'error': 'SELF_REGISTRATION_DISABLED',
        'contact': 'يرجى التواصل مع إدارة اللجنة العليا للحصول على حساب'
    }), 403

@auth_bp.route('/login', methods=['POST'])
@rate_limit("5 per 15 minutes")
def login():
    try:
        data = request.get_json()
        
        schema = UserLoginSchema()
        try:
            validated_data = schema.load(data)
        except ValidationError as err:
            return jsonify({'message': 'بيانات تسجيل الدخول غير صالحة', 'errors': err.messages}), 400
        
        username = validated_data['username']
        password = validated_data['password']
        ip_address = request.remote_addr or 'Unknown'
        
        is_locked, locked_until = lockout_service.is_account_locked(username)
        if is_locked:
            remaining_time = int((locked_until - datetime.utcnow()).total_seconds() / 60)
            return jsonify({
                'message': f'الحساب مقفل بسبب محاولات تسجيل دخول فاشلة متعددة. يرجى المحاولة بعد {remaining_time} دقيقة',
                'account_locked': True,
                'locked_until': locked_until.isoformat()
            }), 403
        
        user = User.query.filter_by(username=username).first()
        
        if not user or not check_password_hash(user.password_hash, password):
            is_locked, locked_until = lockout_service.record_failed_attempt(username, ip_address)
            
            if is_locked:
                enqueue_notification(
                    user_id=user.user_id if user else None,
                    notification_type='account_locked',
                    message='تم قفل حسابك بسبب محاولات تسجيل دخول فاشلة متعددة',
                    channel='email',
                    username=username,
                    email=user.email if user else None
                )
                return jsonify({
                    'message': 'تم قفل الحساب بسبب محاولات تسجيل دخول فاشلة متعددة',
                    'account_locked': True
                }), 403
            
            remaining = lockout_service.get_remaining_attempts(username, ip_address)
            return jsonify({
                'message': f'اسم المستخدم أو كلمة المرور غير صحيحة. المحاولات المتبقية: {remaining}',
                'remaining_attempts': remaining
            }), 401
        
        if not user.is_active:
            return jsonify({'message': 'الحساب غير نشط'}), 401
        
        # Handle 2FA if enabled
        if user.two_factor_enabled:
            otp_code = validated_data.get('otp_code')
            
            # If OTP code not provided, request it
            if not otp_code:
                return jsonify({
                    'requires_2fa': True,
                    'message': 'يرجى إدخال رمز المصادقة الثنائية',
                    'username': user.username
                }), 200
            
            # Verify OTP code
            totp = pyotp.TOTP(user.two_factor_secret)
            if not totp.verify(otp_code, valid_window=1):
                is_locked, locked_until = lockout_service.record_failed_attempt(username, ip_address)
                
                if is_locked:
                    return jsonify({
                        'message': 'تم قفل الحساب بسبب محاولات تسجيل دخول فاشلة متعددة',
                        'account_locked': True
                    }), 403
                
                remaining = lockout_service.get_remaining_attempts(username, ip_address)
                return jsonify({
                    'message': f'رمز التحقق غير صحيح. المحاولات المتبقية: {remaining}',
                    'remaining_attempts': remaining
                }), 401
        
        lockout_service.clear_failed_attempts(username, ip_address)
        
        access_token_exp = int(os.environ.get('ACCESS_TOKEN_HOURS', 1))
        refresh_token_days = int(os.environ.get('REFRESH_TOKEN_DAYS', 30))
        
        access_token = jwt.encode({
            'user_id': user.user_id,
            'exp': datetime.utcnow() + timedelta(hours=access_token_exp)
        }, current_app.config['SECRET_KEY'], algorithm='HS256')
        
        refresh_token = session_service.create_session(user.user_id, expires_days=refresh_token_days)
        
        return jsonify({
            'requires_2fa': False,
            'message': 'تم تسجيل الدخول بنجاح',
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer',
            'expires_in': access_token_exp * 3600,
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'خطأ أثناء تسجيل الدخول: {str(e)}'}), 500

@auth_bp.route('/refresh', methods=['POST'])
@rate_limit("10 per minute")
def refresh_token():
    """Refresh access token using refresh token"""
    try:
        data = request.get_json()
        
        schema = RefreshTokenSchema()
        try:
            validated_data = schema.load(data)
        except ValidationError as err:
            return jsonify({'message': 'بيانات غير صالحة', 'errors': err.messages}), 400
        
        refresh_token = validated_data['refresh_token']
        
        session_data = session_service.validate_session(refresh_token)
        if not session_data:
            return jsonify({'message': 'رمز التحديث غير صالح أو منتهي الصلاحية'}), 401
        
        user = User.query.filter_by(user_id=session_data['user_id']).first()
        if not user or not user.is_active:
            return jsonify({'message': 'المستخدم غير موجود أو غير نشط'}), 401
        
        access_token_exp = int(os.environ.get('ACCESS_TOKEN_HOURS', 1))
        access_token = jwt.encode({
            'user_id': user.user_id,
            'exp': datetime.utcnow() + timedelta(hours=access_token_exp)
        }, current_app.config['SECRET_KEY'], algorithm='HS256')
        
        session_service.revoke_session(refresh_token)
        refresh_token_days = int(os.environ.get('REFRESH_TOKEN_DAYS', 30))
        new_refresh_token = session_service.create_session(user.user_id, expires_days=refresh_token_days)
        
        return jsonify({
            'message': 'تم تحديث الرمز بنجاح',
            'access_token': access_token,
            'refresh_token': new_refresh_token,
            'token_type': 'Bearer',
            'expires_in': access_token_exp * 3600
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'خطأ في تحديث الرمز: {str(e)}'}), 500

@auth_bp.route('/logout', methods=['POST'])
@token_required
def logout(current_user):
    """Logout and revoke refresh token"""
    try:
        data = request.get_json() or {}
        
        if 'refresh_token' in data:
            session_service.revoke_session(data['refresh_token'])
        else:
            session_service.revoke_all_user_sessions(current_user.user_id)
        
        return jsonify({'message': 'تم تسجيل الخروج بنجاح'}), 200
        
    except Exception as e:
        return jsonify({'message': f'خطأ في تسجيل الخروج: {str(e)}'}), 500

@auth_bp.route('/sessions', methods=['GET'])
@token_required
def get_sessions(current_user):
    """Get all active sessions for current user"""
    try:
        sessions = session_service.get_user_sessions(current_user.user_id)
        
        return jsonify({
            'sessions': [{
                'device': s.get('device'),
                'ip_address': s.get('ip_address'),
                'created_at': s.get('created_at'),
                'last_used': s.get('last_used'),
                'token': s.get('refresh_token')[:8] + '...'
            } for s in sessions]
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'خطأ في جلب الجلسات: {str(e)}'}), 500

@auth_bp.route('/sessions/revoke', methods=['POST'])
@token_required
def revoke_session(current_user):
    """Revoke a specific session"""
    try:
        data = request.get_json()
        
        schema = RevokeSessionSchema()
        try:
            validated_data = schema.load(data)
        except ValidationError as err:
            return jsonify({'message': 'بيانات غير صالحة', 'errors': err.messages}), 400
        
        success = session_service.revoke_session(validated_data['refresh_token'])
        
        if success:
            return jsonify({'message': 'تم إلغاء الجلسة بنجاح'}), 200
        else:
            return jsonify({'message': 'الجلسة غير موجودة'}), 404
        
    except Exception as e:
        return jsonify({'message': f'خطأ في إلغاء الجلسة: {str(e)}'}), 500

@auth_bp.route('/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    return jsonify({'user': current_user.to_dict()}), 200

@auth_bp.route('/profile', methods=['PUT'])
@token_required
def update_profile(current_user):
    try:
        data = request.get_json()
        
        schema = UserUpdateSchema()
        try:
            validated_data = schema.load(data)
        except ValidationError as err:
            return jsonify({'message': 'بيانات غير صالحة', 'errors': err.messages}), 400
        
        if 'full_name' in validated_data:
            current_user.full_name = validated_data['full_name']
        if 'phone_number' in validated_data:
            current_user.phone_number = validated_data['phone_number']
        if 'address' in validated_data:
            current_user.address = validated_data['address']
        if 'email' in validated_data:
            existing_user = User.query.filter_by(email=validated_data['email']).first()
            if existing_user and existing_user.user_id != current_user.user_id:
                return jsonify({'message': 'البريد الإلكتروني مستخدم مسبقاً'}), 400
            current_user.email = validated_data['email']
        
        current_user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'تم تحديث الملف الشخصي بنجاح',
            'user': current_user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'خطأ في تحديث الملف الشخصي: {str(e)}'}), 500

@auth_bp.route('/change-password', methods=['POST'])
@token_required
@rate_limit("3 per hour")
def change_password(current_user):
    try:
        data = request.get_json()
        
        schema = ChangePasswordSchema()
        try:
            validated_data = schema.load(data)
        except ValidationError as err:
            return jsonify({'message': 'بيانات غير صالحة', 'errors': err.messages}), 400
        
        if not check_password_hash(current_user.password_hash, validated_data['current_password']):
            return jsonify({'message': 'كلمة المرور الحالية غير صحيحة'}), 400
        
        is_valid, errors = validate_password_strength(validated_data['new_password'])
        if not is_valid:
            return jsonify({'message': 'كلمة المرور الجديدة ضعيفة', 'errors': errors}), 400
        
        if current_user.password_history:
            try:
                history = json.loads(current_user.password_history)
                for old_hash in history[-3:]:
                    if check_password_hash(old_hash, validated_data['new_password']):
                        return jsonify({'message': 'لا يمكن استخدام كلمة مرور سبق استخدامها'}), 400
            except:
                history = []
        else:
            history = []
        
        new_hash = generate_password_hash(validated_data['new_password'])
        history.append(current_user.password_hash)
        history = history[-3:]
        
        current_user.password_hash = new_hash
        current_user.password_history = json.dumps(history)
        current_user.last_password_change = datetime.utcnow()
        current_user.updated_at = datetime.utcnow()
        db.session.commit()
        
        session_service.revoke_all_user_sessions(current_user.user_id)
        
        return jsonify({'message': 'تم تغيير كلمة المرور بنجاح. يرجى تسجيل الدخول مرة أخرى'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'خطأ في تغيير كلمة المرور: {str(e)}'}), 500

@auth_bp.route('/roles', methods=['GET'])
def get_roles():
    try:
        roles = Role.query.all()
        return jsonify({'roles': [role.to_dict() for role in roles]}), 200
    except Exception as e:
        return jsonify({'message': f'خطأ في جلب الأدوار: {str(e)}'}), 500

@auth_bp.route('/2fa/enable', methods=['POST'])
@token_required
def enable_2fa(current_user):
    """Enable 2FA for the current user"""
    try:
        if current_user.two_factor_enabled:
            return jsonify({'message': 'المصادقة الثنائية مفعلة بالفعل'}), 400
        
        secret = pyotp.random_base32()
        current_user.two_factor_secret = secret
        
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=current_user.email,
            issuer_name='نظام الشكاوى الإلكتروني'
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        db.session.commit()
        
        return jsonify({
            'message': 'تم إنشاء مفتاح المصادقة الثنائية. يرجى مسح رمز QR باستخدام تطبيق المصادقة',
            'secret': secret,
            'qr_code': f'data:image/png;base64,{img_str}',
            'manual_entry': provisioning_uri
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'خطأ في تفعيل المصادقة الثنائية: {str(e)}'}), 500

@auth_bp.route('/2fa/verify', methods=['POST'])
@token_required
def verify_2fa_setup(current_user):
    """Verify 2FA setup with a code"""
    try:
        data = request.get_json()
        
        if 'code' not in data:
            return jsonify({'message': 'رمز التحقق مطلوب'}), 400
        
        if not current_user.two_factor_secret:
            return jsonify({'message': 'لم يتم إعداد المصادقة الثنائية'}), 400
        
        totp = pyotp.TOTP(current_user.two_factor_secret)
        if totp.verify(data['code']):
            current_user.two_factor_enabled = True
            db.session.commit()
            return jsonify({'message': 'تم تفعيل المصادقة الثنائية بنجاح'}), 200
        else:
            return jsonify({'message': 'رمز التحقق غير صحيح'}), 400
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'خطأ في التحقق: {str(e)}'}), 500

@auth_bp.route('/2fa/disable', methods=['POST'])
@token_required
def disable_2fa(current_user):
    """Disable 2FA for the current user"""
    try:
        data = request.get_json()
        
        if not current_user.two_factor_enabled:
            return jsonify({'message': 'المصادقة الثنائية غير مفعلة'}), 400
        
        if 'password' not in data:
            return jsonify({'message': 'كلمة المرور مطلوبة لإيقاف المصادقة الثنائية'}), 400
        
        if not check_password_hash(current_user.password_hash, data['password']):
            return jsonify({'message': 'كلمة المرور غير صحيحة'}), 401
        
        current_user.two_factor_enabled = False
        current_user.two_factor_secret = None
        db.session.commit()
        
        return jsonify({'message': 'تم إيقاف المصادقة الثنائية بنجاح'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'خطأ في إيقاف المصادقة الثنائية: {str(e)}'}), 500

@auth_bp.route('/2fa/validate', methods=['POST'])
@rate_limit("5 per 15 minutes")
def validate_2fa():
    """Validate 2FA code during login"""
    try:
        data = request.get_json()
        
        if not data.get('username') or not data.get('code'):
            return jsonify({'message': 'اسم المستخدم ورمز التحقق مطلوبان'}), 400
        
        user = User.query.filter_by(username=data['username']).first()
        
        if not user or not user.two_factor_enabled:
            return jsonify({'message': 'بيانات غير صحيحة'}), 401
        
        totp = pyotp.TOTP(user.two_factor_secret)
        if totp.verify(data['code']):
            access_token_exp = int(os.environ.get('ACCESS_TOKEN_HOURS', 1))
            refresh_token_days = int(os.environ.get('REFRESH_TOKEN_DAYS', 30))
            
            access_token = jwt.encode({
                'user_id': user.user_id,
                'exp': datetime.utcnow() + timedelta(hours=access_token_exp)
            }, current_app.config['SECRET_KEY'], algorithm='HS256')
            
            refresh_token = session_service.create_session(user.user_id, expires_days=refresh_token_days)
            
            return jsonify({
                'message': 'تم تسجيل الدخول بنجاح',
                'access_token': access_token,
                'refresh_token': refresh_token,
                'token_type': 'Bearer',
                'expires_in': access_token_exp * 3600,
                'user': user.to_dict()
            }), 200
        else:
            return jsonify({'message': 'رمز التحقق غير صحيح'}), 401
        
    except Exception as e:
        return jsonify({'message': f'خطأ في التحقق: {str(e)}'}), 500
