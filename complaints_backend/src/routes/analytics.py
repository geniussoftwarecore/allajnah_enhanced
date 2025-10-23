from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
from sqlalchemy import func, extract, and_, or_
from src.routes.auth import token_required, role_required, rate_limit
from src.models.complaint import (
    db, Complaint, Payment, User, Subscription, ComplaintCategory,
    ComplaintStatus, Settings
)
from src.core.cache import cache_get, cache_set

analytics_bp = Blueprint('analytics', __name__)

CACHE_TIMEOUT = 3600


@analytics_bp.route('/analytics/dashboard', methods=['GET'])
@token_required
@role_required(['Higher Committee', 'Technical Committee'])
@rate_limit('60 per hour')
def get_dashboard_analytics(current_user):
    """Get overview statistics for dashboard"""
    try:
        cache_key = 'analytics:dashboard'
        cached_data = cache_get(cache_key)
        if cached_data:
            return jsonify(cached_data), 200
        
        now = datetime.utcnow()
        month_ago = now - timedelta(days=30)
        
        total_complaints = Complaint.query.count()
        recent_complaints = Complaint.query.filter(Complaint.submitted_at >= month_ago).count()
        
        active_users = User.query.filter_by(is_active=True).count()
        
        active_subscriptions = Subscription.query.filter_by(status='active').count()
        
        total_revenue = db.session.query(func.sum(Payment.amount)).filter(
            Payment.status == 'approved'
        ).scalar() or 0
        
        monthly_revenue = db.session.query(func.sum(Payment.amount)).filter(
            and_(
                Payment.status == 'approved',
                Payment.created_at >= month_ago
            )
        ).scalar() or 0
        
        closed_status = ComplaintStatus.query.filter_by(status_name='مغلقة').first()
        closed_count = 0
        if closed_status:
            closed_count = Complaint.query.filter_by(status_id=closed_status.status_id).count()
        
        resolution_rate = (closed_count / total_complaints * 100) if total_complaints > 0 else 0
        
        closed_complaints = Complaint.query.filter(
            and_(
                Complaint.closed_at.isnot(None),
                Complaint.submitted_at.isnot(None)
            )
        ).all()
        
        if closed_complaints:
            total_days = sum([(c.closed_at - c.submitted_at).days for c in closed_complaints])
            avg_response_time = total_days / len(closed_complaints)
        else:
            avg_response_time = 0
        
        pending_payments = Payment.query.filter_by(status='pending').count()
        
        approved_payments = Payment.query.filter_by(status='approved').count()
        rejected_payments = Payment.query.filter_by(status='rejected').count()
        total_payments = Payment.query.count()
        
        approval_rate = (approved_payments / total_payments * 100) if total_payments > 0 else 0
        
        currency_setting = Settings.query.filter_by(key='currency').first()
        currency = currency_setting.value if currency_setting else 'YER'
        
        result = {
            'overview': {
                'total_complaints': total_complaints,
                'recent_complaints_30d': recent_complaints,
                'active_users': active_users,
                'active_subscriptions': active_subscriptions,
                'total_revenue': round(total_revenue, 2),
                'monthly_revenue': round(monthly_revenue, 2),
                'currency': currency
            },
            'complaints_metrics': {
                'total': total_complaints,
                'closed': closed_count,
                'resolution_rate': round(resolution_rate, 2),
                'avg_response_time_days': round(avg_response_time, 2)
            },
            'payments_metrics': {
                'total': total_payments,
                'pending': pending_payments,
                'approved': approved_payments,
                'rejected': rejected_payments,
                'approval_rate': round(approval_rate, 2)
            },
            'generated_at': now.isoformat()
        }
        
        cache_set(cache_key, result, CACHE_TIMEOUT)
        
        return jsonify(result), 200
    
    except Exception as e:
        current_app.logger.error(f'Error fetching dashboard analytics: {str(e)}')
        return jsonify({'error': 'فشل جلب إحصائيات لوحة التحكم'}), 500


@analytics_bp.route('/analytics/complaints/trends', methods=['GET'])
@token_required
@role_required(['Higher Committee', 'Technical Committee'])
@rate_limit('60 per hour')
def get_complaints_trends(current_user):
    """Get time-series data for complaints"""
    try:
        period = request.args.get('period', 'month')
        
        if period not in ['day', 'week', 'month']:
            return jsonify({'error': 'فترة غير صالحة. استخدم: day, week, month'}), 400
        
        cache_key = f'analytics:complaints_trends:{period}'
        cached_data = cache_get(cache_key)
        if cached_data:
            return jsonify(cached_data), 200
        
        now = datetime.utcnow()
        
        if period == 'day':
            start_date = now - timedelta(days=30)
            group_format = '%Y-%m-%d'
        elif period == 'week':
            start_date = now - timedelta(weeks=12)
            group_format = '%Y-W%W'
        else:
            start_date = now - timedelta(days=365)
            group_format = '%Y-%m'
        
        complaints = Complaint.query.filter(Complaint.submitted_at >= start_date).all()
        
        time_series = {}
        for complaint in complaints:
            if complaint.submitted_at:
                key = complaint.submitted_at.strftime(group_format)
                time_series[key] = time_series.get(key, 0) + 1
        
        time_series_list = [
            {'period': k, 'count': v}
            for k, v in sorted(time_series.items())
        ]
        
        by_category = db.session.query(
            ComplaintCategory.category_name,
            func.count(Complaint.complaint_id).label('count')
        ).join(Complaint).filter(
            Complaint.submitted_at >= start_date
        ).group_by(ComplaintCategory.category_name).all()
        
        category_breakdown = [
            {'category': cat, 'count': count}
            for cat, count in by_category
        ]
        
        by_status = db.session.query(
            ComplaintStatus.status_name,
            func.count(Complaint.complaint_id).label('count')
        ).join(Complaint).filter(
            Complaint.submitted_at >= start_date
        ).group_by(ComplaintStatus.status_name).all()
        
        status_distribution = [
            {'status': status, 'count': count}
            for status, count in by_status
        ]
        
        result = {
            'period': period,
            'time_series': time_series_list,
            'by_category': category_breakdown,
            'by_status': status_distribution,
            'generated_at': now.isoformat()
        }
        
        cache_set(cache_key, result, CACHE_TIMEOUT)
        
        return jsonify(result), 200
    
    except Exception as e:
        current_app.logger.error(f'Error fetching complaints trends: {str(e)}')
        return jsonify({'error': 'فشل جلب اتجاهات الشكاوى'}), 500


@analytics_bp.route('/analytics/subscriptions/metrics', methods=['GET'])
@token_required
@role_required(['Higher Committee'])
@rate_limit('60 per hour')
def get_subscription_metrics(current_user):
    """Get subscription analytics and metrics"""
    try:
        cache_key = 'analytics:subscriptions'
        cached_data = cache_get(cache_key)
        if cached_data:
            return jsonify(cached_data), 200
        
        now = datetime.utcnow()
        
        active_subs = Subscription.query.filter_by(status='active').count()
        expired_subs = Subscription.query.filter_by(status='expired').count()
        
        grace_period_setting = Settings.query.filter_by(key='grace_period_days').first()
        grace_period_days = int(grace_period_setting.value) if grace_period_setting else 7
        
        enable_grace_period = Settings.query.filter_by(key='enable_grace_period').first()
        grace_enabled = enable_grace_period.value.lower() == 'true' if enable_grace_period else True
        
        grace_period_subs = 0
        if grace_enabled:
            active_subs_all = Subscription.query.filter_by(status='active').all()
            for sub in active_subs_all:
                if sub.end_date < now and sub.grace_period_enabled:
                    grace_end = sub.end_date + timedelta(days=grace_period_days)
                    if now <= grace_end:
                        grace_period_subs += 1
        
        total_subs = Subscription.query.count()
        renewal_subs = Subscription.query.filter_by(is_renewal=True).count()
        
        renewal_rate = (renewal_subs / total_subs * 100) if total_subs > 0 else 0
        
        expiring_soon = Subscription.query.filter(
            and_(
                Subscription.status == 'active',
                Subscription.end_date <= now + timedelta(days=30),
                Subscription.end_date > now
            )
        ).count()
        
        next_month = now + timedelta(days=30)
        next_month_end = now + timedelta(days=60)
        
        projected_renewals = Subscription.query.filter(
            and_(
                Subscription.status == 'active',
                Subscription.end_date >= next_month,
                Subscription.end_date < next_month_end
            )
        ).count()
        
        subscription_price = Settings.query.filter_by(key='subscription_price').first()
        price = float(subscription_price.value) if subscription_price else 0
        
        projected_revenue = projected_renewals * price * (renewal_rate / 100)
        
        currency_setting = Settings.query.filter_by(key='currency').first()
        currency = currency_setting.value if currency_setting else 'YER'
        
        result = {
            'total_subscriptions': total_subs,
            'active_subscriptions': active_subs,
            'expired_subscriptions': expired_subs,
            'grace_period_subscriptions': grace_period_subs,
            'renewal_subscriptions': renewal_subs,
            'renewal_rate': round(renewal_rate, 2),
            'expiring_soon_30d': expiring_soon,
            'projections': {
                'next_month_renewals': projected_renewals,
                'projected_revenue': round(projected_revenue, 2),
                'currency': currency
            },
            'generated_at': now.isoformat()
        }
        
        cache_set(cache_key, result, CACHE_TIMEOUT)
        
        return jsonify(result), 200
    
    except Exception as e:
        current_app.logger.error(f'Error fetching subscription metrics: {str(e)}')
        return jsonify({'error': 'فشل جلب إحصائيات الاشتراكات'}), 500


@analytics_bp.route('/analytics/payments/summary', methods=['GET'])
@token_required
@role_required(['Higher Committee'])
@rate_limit('60 per hour')
def get_payment_summary(current_user):
    """Get payment analytics and summary"""
    try:
        period = request.args.get('period', 'month')
        
        if period not in ['week', 'month', 'quarter', 'year', 'all']:
            return jsonify({'error': 'فترة غير صالحة. استخدم: week, month, quarter, year, all'}), 400
        
        cache_key = f'analytics:payments:{period}'
        cached_data = cache_get(cache_key)
        if cached_data:
            return jsonify(cached_data), 200
        
        now = datetime.utcnow()
        
        if period == 'week':
            start_date = now - timedelta(days=7)
        elif period == 'month':
            start_date = now - timedelta(days=30)
        elif period == 'quarter':
            start_date = now - timedelta(days=90)
        elif period == 'year':
            start_date = now - timedelta(days=365)
        else:
            start_date = datetime(2020, 1, 1)
        
        payments_query = Payment.query.filter(Payment.created_at >= start_date)
        
        total_payments = payments_query.count()
        approved_payments = payments_query.filter_by(status='approved').count()
        rejected_payments = payments_query.filter_by(status='rejected').count()
        pending_payments = payments_query.filter_by(status='pending').count()
        
        total_revenue = db.session.query(func.sum(Payment.amount)).filter(
            and_(
                Payment.created_at >= start_date,
                Payment.status == 'approved'
            )
        ).scalar() or 0
        
        by_method = db.session.query(
            Payment.method_id,
            func.count(Payment.payment_id).label('count'),
            func.sum(Payment.amount).label('total')
        ).filter(
            and_(
                Payment.created_at >= start_date,
                Payment.status == 'approved'
            )
        ).group_by(Payment.method_id).all()
        
        from src.models.complaint import PaymentMethod
        
        method_distribution = []
        for method_id, count, total in by_method:
            method = PaymentMethod.query.get(method_id)
            if method:
                method_distribution.append({
                    'method': method.name,
                    'count': count,
                    'total_amount': round(float(total) if total else 0, 2)
                })
        
        approval_rate = (approved_payments / total_payments * 100) if total_payments > 0 else 0
        rejection_rate = (rejected_payments / total_payments * 100) if total_payments > 0 else 0
        
        avg_payment = total_revenue / approved_payments if approved_payments > 0 else 0
        
        currency_setting = Settings.query.filter_by(key='currency').first()
        currency = currency_setting.value if currency_setting else 'YER'
        
        result = {
            'period': period,
            'total_payments': total_payments,
            'approved_payments': approved_payments,
            'rejected_payments': rejected_payments,
            'pending_payments': pending_payments,
            'total_revenue': round(total_revenue, 2),
            'average_payment': round(avg_payment, 2),
            'approval_rate': round(approval_rate, 2),
            'rejection_rate': round(rejection_rate, 2),
            'by_method': method_distribution,
            'currency': currency,
            'generated_at': now.isoformat()
        }
        
        cache_set(cache_key, result, CACHE_TIMEOUT)
        
        return jsonify(result), 200
    
    except Exception as e:
        current_app.logger.error(f'Error fetching payment summary: {str(e)}')
        return jsonify({'error': 'فشل جلب ملخص المدفوعات'}), 500


@analytics_bp.route('/analytics/users/stats', methods=['GET'])
@token_required
@role_required(['Higher Committee'])
@rate_limit('60 per hour')
def get_user_statistics(current_user):
    """Get user statistics by role and activity"""
    try:
        cache_key = 'analytics:users'
        cached_data = cache_get(cache_key)
        if cached_data:
            return jsonify(cached_data), 200
        
        total_users = User.query.count()
        active_users = User.query.filter_by(is_active=True).count()
        inactive_users = total_users - active_users
        
        by_role = db.session.query(
            db.Model.metadata.tables['roles'].c.role_name,
            func.count(User.user_id).label('count')
        ).join(
            db.Model.metadata.tables['roles'],
            User.role_id == db.Model.metadata.tables['roles'].c.role_id
        ).group_by(db.Model.metadata.tables['roles'].c.role_name).all()
        
        role_distribution = [
            {'role': role, 'count': count}
            for role, count in by_role
        ]
        
        two_fa_enabled = User.query.filter_by(two_factor_enabled=True).count()
        two_fa_rate = (two_fa_enabled / total_users * 100) if total_users > 0 else 0
        
        now = datetime.utcnow()
        month_ago = now - timedelta(days=30)
        
        new_users_30d = User.query.filter(User.created_at >= month_ago).count()
        
        result = {
            'total_users': total_users,
            'active_users': active_users,
            'inactive_users': inactive_users,
            'new_users_30d': new_users_30d,
            'by_role': role_distribution,
            'two_factor_enabled': two_fa_enabled,
            'two_factor_rate': round(two_fa_rate, 2),
            'generated_at': now.isoformat()
        }
        
        cache_set(cache_key, result, CACHE_TIMEOUT)
        
        return jsonify(result), 200
    
    except Exception as e:
        current_app.logger.error(f'Error fetching user statistics: {str(e)}')
        return jsonify({'error': 'فشل جلب إحصائيات المستخدمين'}), 500


@analytics_bp.route('/analytics/cache/clear', methods=['POST'])
@token_required
@role_required(['Higher Committee'])
@rate_limit('10 per hour')
def clear_analytics_cache(current_user):
    """Clear analytics cache (admin only)"""
    try:
        from src.core.cache import cache_clear_pattern
        
        cleared = cache_clear_pattern('analytics:*')
        
        return jsonify({
            'message': 'تم مسح ذاكرة التخزين المؤقت للتحليلات',
            'cleared_keys': cleared
        }), 200
    
    except Exception as e:
        current_app.logger.error(f'Error clearing analytics cache: {str(e)}')
        return jsonify({'error': 'فشل مسح ذاكرة التخزين المؤقت'}), 500
