from flask import Blueprint, request, jsonify
from src.database.db import db
from src.models.complaint import User, AuditLog, Role
from src.routes.auth import token_required, role_required
from datetime import datetime, timedelta
import pyotp
import qrcode
import io
import base64
from werkzeug.security import check_password_hash

security_api_bp = Blueprint('security_api', __name__, url_prefix='/api/security')

@security_api_bp.route('/2fa/setup', methods=['POST'])
@token_required
@role_required(['admin', 'support'])
def setup_2fa(current_user):
    try:
        secret = pyotp.random_base32()
        
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=current_user.email,
            issuer_name='نظام اللجنة المحسّنة'
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        qr_code_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        
        return jsonify({
            'secret': secret,
            'qr_code': f'data:image/png;base64,{qr_code_base64}',
            'manual_entry_key': secret
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@security_api_bp.route('/2fa/enable', methods=['POST'])
@token_required
@role_required(['admin', 'support'])
def enable_2fa(current_user):
    try:
        data = request.get_json()
        secret = data.get('secret')
        verification_code = data.get('code')
        
        if not secret or not verification_code:
            return jsonify({'error': 'الرمز السري وكود التحقق مطلوبان'}), 400
        
        totp = pyotp.TOTP(secret)
        if not totp.verify(verification_code, valid_window=1):
            return jsonify({'error': 'كود التحقق غير صحيح'}), 400
        
        current_user.two_factor_secret = secret
        current_user.two_factor_enabled = True
        
        audit_log = AuditLog(
            action_type='2fa_enabled',
            performed_by_id=current_user.user_id,
            affected_user_id=current_user.user_id,
            details=f'تم تفعيل المصادقة الثنائية للمستخدم {current_user.full_name}',
            timestamp=datetime.utcnow()
        )
        db.session.add(audit_log)
        db.session.commit()
        
        return jsonify({'message': 'تم تفعيل المصادقة الثنائية بنجاح'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@security_api_bp.route('/2fa/disable', methods=['POST'])
@token_required
@role_required(['admin', 'support'])
def disable_2fa(current_user):
    try:
        data = request.get_json()
        password = data.get('password')
        
        if not password:
            return jsonify({'error': 'كلمة المرور مطلوبة'}), 400
        
        if not check_password_hash(current_user.password_hash, password):
            return jsonify({'error': 'كلمة مرور غير صحيحة'}), 401
        
        current_user.two_factor_enabled = False
        current_user.two_factor_secret = None
        
        audit_log = AuditLog(
            action_type='2fa_disabled',
            performed_by_id=current_user.user_id,
            affected_user_id=current_user.user_id,
            details=f'تم تعطيل المصادقة الثنائية للمستخدم {current_user.full_name}',
            timestamp=datetime.utcnow()
        )
        db.session.add(audit_log)
        db.session.commit()
        
        return jsonify({'message': 'تم تعطيل المصادقة الثنائية بنجاح'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@security_api_bp.route('/audit-log', methods=['GET'])
@token_required
@role_required(['admin'])
def get_audit_log(current_user):
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        action_type = request.args.get('action_type')
        user_id = request.args.get('user_id')
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        
        query = AuditLog.query
        
        if action_type:
            query = query.filter_by(action_type=action_type)
        
        if user_id:
            query = query.filter(
                db.or_(
                    AuditLog.performed_by_id == user_id,
                    AuditLog.affected_user_id == user_id
                )
            )
        
        if from_date:
            from_dt = datetime.fromisoformat(from_date.replace('Z', '+00:00'))
            query = query.filter(AuditLog.timestamp >= from_dt)
        
        if to_date:
            to_dt = datetime.fromisoformat(to_date.replace('Z', '+00:00'))
            query = query.filter(AuditLog.timestamp <= to_dt)
        
        paginated = query.order_by(AuditLog.timestamp.desc()).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        logs = []
        for log in paginated.items:
            log_dict = log.to_dict()
            if log.performed_by:
                log_dict['performed_by_name'] = log.performed_by.full_name
            if log.affected_user:
                log_dict['affected_user_name'] = log.affected_user.full_name
            logs.append(log_dict)
        
        return jsonify({
            'logs': logs,
            'total': paginated.total,
            'pages': paginated.pages,
            'current_page': paginated.page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@security_api_bp.route('/security-events', methods=['GET'])
@token_required
@role_required(['admin'])
def get_security_events(current_user):
    try:
        days = request.args.get('days', 30, type=int)
        from_date = datetime.utcnow() - timedelta(days=days)
        
        security_actions = [
            'login_success',
            'login_failed',
            'password_changed',
            'role_changed',
            '2fa_enabled',
            '2fa_disabled',
            'account_locked',
            'account_unlocked'
        ]
        
        events = AuditLog.query.filter(
            AuditLog.action_type.in_(security_actions),
            AuditLog.timestamp >= from_date
        ).order_by(AuditLog.timestamp.desc()).limit(100).all()
        
        result = []
        for event in events:
            event_dict = event.to_dict()
            if event.performed_by:
                event_dict['performed_by_name'] = event.performed_by.full_name
            if event.affected_user:
                event_dict['affected_user_name'] = event.affected_user.full_name
            result.append(event_dict)
        
        return jsonify({'events': result}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@security_api_bp.route('/stats', methods=['GET'])
@token_required
@role_required(['admin'])
def get_security_stats(current_user):
    try:
        days = request.args.get('days', 30, type=int)
        from_date = datetime.utcnow() - timedelta(days=days)
        
        total_logins = AuditLog.query.filter(
            AuditLog.action_type == 'login_success',
            AuditLog.timestamp >= from_date
        ).count()
        
        failed_logins = AuditLog.query.filter(
            AuditLog.action_type == 'login_failed',
            AuditLog.timestamp >= from_date
        ).count()
        
        password_changes = AuditLog.query.filter(
            AuditLog.action_type == 'password_changed',
            AuditLog.timestamp >= from_date
        ).count()
        
        users_with_2fa = User.query.filter_by(two_factor_enabled=True).count()
        admin_role = Role.query.filter_by(role_name='admin').first()
        support_role = Role.query.filter_by(role_name='support').first()
        
        admin_role_ids = []
        if admin_role:
            admin_role_ids.append(admin_role.role_id)
        if support_role:
            admin_role_ids.append(support_role.role_id)
        
        total_admins = User.query.filter(User.role_id.in_(admin_role_ids)).count() if admin_role_ids else 0
        
        return jsonify({
            'total_logins': total_logins,
            'failed_logins': failed_logins,
            'password_changes': password_changes,
            'users_with_2fa': users_with_2fa,
            'total_admin_users': total_admins,
            '2fa_adoption_rate': round((users_with_2fa / total_admins * 100), 2) if total_admins > 0 else 0
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
