from flask import Blueprint, request, jsonify
from src.database.db import db
from src.models.complaint import User, Subscription
from src.routes.auth import token_required, role_required
from datetime import datetime, timedelta

subscription_api_bp = Blueprint('subscription_api', __name__, url_prefix='/api/subscriptions')

@subscription_api_bp.route('/user/<user_id>/status', methods=['GET'])
@token_required
def get_user_subscription_status(current_user, user_id):
    try:
        if current_user.user_id != user_id and current_user.role.role_name not in ['admin', 'support']:
            return jsonify({'error': 'غير مصرح'}), 403
        
        subscription = Subscription.query.filter_by(
            user_id=user_id,
            status='active'
        ).order_by(Subscription.end_date.desc()).first()
        
        if not subscription:
            expired_sub = Subscription.query.filter_by(
                user_id=user_id,
                status='expired'
            ).order_by(Subscription.end_date.desc()).first()
            
            if expired_sub:
                return jsonify(expired_sub.to_dict()), 200
            
            return jsonify({'error': 'لا يوجد اشتراك'}), 404
        
        return jsonify(subscription.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@subscription_api_bp.route('/admin/all', methods=['GET'])
@token_required
@role_required(['admin'])
def get_all_subscriptions(current_user):
    try:
        subscriptions = Subscription.query.order_by(Subscription.end_date.desc()).all()
        
        result = []
        for sub in subscriptions:
            sub_dict = sub.to_dict()
            user = User.query.get(sub.user_id)
            if user:
                sub_dict['user_name'] = user.full_name
                sub_dict['user_email'] = user.email
            result.append(sub_dict)
        
        return jsonify({'subscriptions': result}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@subscription_api_bp.route('/admin/<subscription_id>/extend', methods=['POST'])
@token_required
@role_required(['admin'])
def extend_subscription(current_user, subscription_id):
    try:
        data = request.get_json()
        months = data.get('months', 12)
        
        subscription = Subscription.query.get(subscription_id)
        if not subscription:
            return jsonify({'error': 'الاشتراك غير موجود'}), 404
        
        current_end_date = subscription.end_date
        now = datetime.utcnow()
        
        if subscription.status == 'expired' or current_end_date < now:
            new_end_date = now + timedelta(days=months * 30)
            subscription.start_date = now
            subscription.status = 'active'
        else:
            new_end_date = current_end_date + timedelta(days=months * 30)
        
        subscription.end_date = new_end_date
        subscription.updated_at = now
        subscription.notified_14d = False
        subscription.notified_7d = False
        subscription.notified_3d = False
        
        db.session.commit()
        
        return jsonify({
            'message': 'تم تمديد الاشتراك بنجاح',
            'subscription': subscription.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@subscription_api_bp.route('/check-access/<user_id>', methods=['GET'])
@token_required
def check_subscription_access(current_user, user_id):
    try:
        if current_user.user_id != user_id and current_user.role.role_name not in ['admin', 'support']:
            return jsonify({'error': 'غير مصرح'}), 403
        
        subscription = Subscription.query.filter_by(
            user_id=user_id
        ).order_by(Subscription.end_date.desc()).first()
        
        if not subscription:
            return jsonify({
                'has_access': False,
                'status': 'no_subscription',
                'message': 'لا يوجد اشتراك'
            }), 200
        
        now = datetime.utcnow()
        end_date = subscription.end_date
        grace_period_days = 7 if subscription.grace_period_enabled else 0
        grace_period_end = end_date + timedelta(days=grace_period_days)
        
        if subscription.status == 'active' and now <= end_date:
            return jsonify({
                'has_access': True,
                'status': 'active',
                'days_remaining': (end_date - now).days,
                'end_date': end_date.isoformat(),
                'message': 'الاشتراك نشط'
            }), 200
        
        elif subscription.grace_period_enabled and now <= grace_period_end:
            return jsonify({
                'has_access': True,
                'status': 'grace_period',
                'days_remaining': (grace_period_end - now).days,
                'end_date': grace_period_end.isoformat(),
                'message': 'فترة السماح نشطة',
                'is_limited': True
            }), 200
        
        else:
            if subscription.status != 'expired':
                subscription.status = 'expired'
                db.session.commit()
            
            return jsonify({
                'has_access': False,
                'status': 'expired',
                'message': 'انتهى الاشتراك'
            }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@subscription_api_bp.route('/admin/stats', methods=['GET'])
@token_required
@role_required(['admin'])
def get_subscription_stats(current_user):
    try:
        now = datetime.utcnow()
        
        total_subscriptions = Subscription.query.count()
        active_subscriptions = Subscription.query.filter_by(status='active').count()
        expired_subscriptions = Subscription.query.filter_by(status='expired').count()
        
        expiring_soon = Subscription.query.filter(
            Subscription.status == 'active',
            Subscription.end_date <= now + timedelta(days=14),
            Subscription.end_date >= now
        ).count()
        
        return jsonify({
            'total': total_subscriptions,
            'active': active_subscriptions,
            'expired': expired_subscriptions,
            'expiring_soon': expiring_soon
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
