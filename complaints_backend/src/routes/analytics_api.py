from flask import Blueprint, jsonify
from src.database.db import db
from src.models.complaint import Complaint, User, Subscription, Payment, ComplaintStatus, ComplaintCategory, Role
from src.routes.auth import token_required, role_required
from datetime import datetime, timedelta
from sqlalchemy import func, extract

analytics_api_bp = Blueprint('analytics_api', __name__, url_prefix='/api/analytics')

@analytics_api_bp.route('/dashboard/summary', methods=['GET'])
@token_required
@role_required(['admin', 'support'])
def get_dashboard_summary(current_user):
    try:
        now = datetime.utcnow()
        last_30_days = now - timedelta(days=30)
        
        total_complaints = Complaint.query.count()
        new_complaints_30d = Complaint.query.filter(
            Complaint.submitted_at >= last_30_days
        ).count()
        
        resolved_status = ComplaintStatus.query.filter_by(status_name='resolved').first()
        resolved_complaints = 0
        if resolved_status:
            resolved_complaints = Complaint.query.filter_by(
                status_id=resolved_status.status_id
            ).count()
        
        total_users = User.query.count()
        trader_role = Role.query.filter_by(role_name='trader').first()
        total_traders = User.query.filter_by(role_id=trader_role.role_id).count() if trader_role else 0
        
        active_subscriptions = Subscription.query.filter_by(status='active').count()
        
        total_revenue = db.session.query(func.sum(Payment.amount)).filter(
            Payment.status == 'approved'
        ).scalar() or 0
        
        avg_resolution_time = None
        resolved_with_dates = Complaint.query.filter(
            Complaint.closed_at.isnot(None),
            Complaint.submitted_at.isnot(None)
        ).all()
        
        if resolved_with_dates:
            total_hours = sum([
                (c.closed_at - c.submitted_at).total_seconds() / 3600
                for c in resolved_with_dates
            ])
            avg_resolution_time = total_hours / len(resolved_with_dates)
        
        return jsonify({
            'total_complaints': total_complaints,
            'new_complaints_30d': new_complaints_30d,
            'resolved_complaints': resolved_complaints,
            'resolution_rate': round((resolved_complaints / total_complaints * 100), 2) if total_complaints > 0 else 0,
            'total_users': total_users,
            'total_traders': total_traders,
            'active_subscriptions': active_subscriptions,
            'total_revenue': float(total_revenue),
            'avg_resolution_time_hours': round(avg_resolution_time, 2) if avg_resolution_time else None
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@analytics_api_bp.route('/complaints/by-status', methods=['GET'])
@token_required
@role_required(['admin', 'support'])
def get_complaints_by_status(current_user):
    try:
        status_counts = db.session.query(
            ComplaintStatus.status_name,
            func.count(Complaint.complaint_id).label('count')
        ).join(Complaint, Complaint.status_id == ComplaintStatus.status_id)\
         .group_by(ComplaintStatus.status_name)\
         .all()
        
        result = [
            {'name': status_name, 'value': count}
            for status_name, count in status_counts
        ]
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@analytics_api_bp.route('/complaints/by-category', methods=['GET'])
@token_required
@role_required(['admin', 'support'])
def get_complaints_by_category(current_user):
    try:
        category_counts = db.session.query(
            ComplaintCategory.category_name,
            func.count(Complaint.complaint_id).label('count')
        ).join(Complaint, Complaint.category_id == ComplaintCategory.category_id)\
         .group_by(ComplaintCategory.category_name)\
         .all()
        
        result = [
            {'name': category_name, 'value': count}
            for category_name, count in category_counts
        ]
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@analytics_api_bp.route('/complaints/by-priority', methods=['GET'])
@token_required
@role_required(['admin', 'support'])
def get_complaints_by_priority(current_user):
    try:
        priority_counts = db.session.query(
            Complaint.priority,
            func.count(Complaint.complaint_id).label('count')
        ).group_by(Complaint.priority)\
         .all()
        
        result = [
            {'name': priority or 'غير محدد', 'value': count}
            for priority, count in priority_counts
        ]
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@analytics_api_bp.route('/complaints/timeline', methods=['GET'])
@token_required
@role_required(['admin', 'support'])
def get_complaints_timeline(current_user):
    try:
        six_months_ago = datetime.utcnow() - timedelta(days=180)
        
        monthly_counts = db.session.query(
            extract('year', Complaint.submitted_at).label('year'),
            extract('month', Complaint.submitted_at).label('month'),
            func.count(Complaint.complaint_id).label('count')
        ).filter(Complaint.submitted_at >= six_months_ago)\
         .group_by('year', 'month')\
         .order_by('year', 'month')\
         .all()
        
        months_ar = ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
                     'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر']
        
        result = [
            {
                'month': f"{months_ar[int(month)-1]} {int(year)}",
                'count': count
            }
            for year, month, count in monthly_counts
        ]
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@analytics_api_bp.route('/revenue/monthly', methods=['GET'])
@token_required
@role_required(['admin'])
def get_monthly_revenue(current_user):
    try:
        six_months_ago = datetime.utcnow() - timedelta(days=180)
        
        monthly_revenue = db.session.query(
            extract('year', Payment.payment_date).label('year'),
            extract('month', Payment.payment_date).label('month'),
            func.sum(Payment.amount).label('total')
        ).filter(
            Payment.status == 'approved',
            Payment.payment_date >= six_months_ago
        ).group_by('year', 'month')\
         .order_by('year', 'month')\
         .all()
        
        months_ar = ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
                     'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر']
        
        result = [
            {
                'month': f"{months_ar[int(month)-1]} {int(year)}",
                'revenue': float(total)
            }
            for year, month, total in monthly_revenue
        ]
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@analytics_api_bp.route('/performance/resolution-time', methods=['GET'])
@token_required
@role_required(['admin', 'support'])
def get_resolution_time_stats(current_user):
    try:
        resolved_complaints = Complaint.query.filter(
            Complaint.closed_at.isnot(None),
            Complaint.submitted_at.isnot(None)
        ).all()
        
        if not resolved_complaints:
            return jsonify({
                'avg_hours': 0,
                'min_hours': 0,
                'max_hours': 0,
                'distribution': []
            }), 200
        
        resolution_times = [
            (c.closed_at - c.submitted_at).total_seconds() / 3600
            for c in resolved_complaints
        ]
        
        avg_time = sum(resolution_times) / len(resolution_times)
        min_time = min(resolution_times)
        max_time = max(resolution_times)
        
        distribution = {
            'أقل من 24 ساعة': len([t for t in resolution_times if t < 24]),
            '1-3 أيام': len([t for t in resolution_times if 24 <= t < 72]),
            '3-7 أيام': len([t for t in resolution_times if 72 <= t < 168]),
            'أكثر من 7 أيام': len([t for t in resolution_times if t >= 168])
        }
        
        return jsonify({
            'avg_hours': round(avg_time, 2),
            'min_hours': round(min_time, 2),
            'max_hours': round(max_time, 2),
            'distribution': [
                {'range': k, 'count': v}
                for k, v in distribution.items()
            ]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
