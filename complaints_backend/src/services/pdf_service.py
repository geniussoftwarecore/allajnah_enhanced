import os
import io
from datetime import datetime, timedelta
from flask import render_template
from weasyprint import HTML
import arabic_reshaper
from bidi.algorithm import get_display
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from src.models.complaint import Complaint, Payment, ComplaintComment, ComplaintAttachment, Subscription, User
from src.database.db import db

class PDFService:
    """Service for generating PDF reports with Arabic RTL support"""
    
    @staticmethod
    def _reshape_arabic_text(text):
        """Reshape Arabic text for proper RTL display"""
        if not text:
            return text
        try:
            reshaped_text = arabic_reshaper.reshape(text)
            bidi_text = get_display(reshaped_text)
            return bidi_text
        except:
            return text
    
    @staticmethod
    def _prepare_template_context(context):
        """Prepare context with reshaped Arabic text"""
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M')
        current_year = datetime.now().year
        
        return {
            **context,
            'current_date': current_date,
            'current_year': current_year
        }
    
    @staticmethod
    def generate_complaint_report(complaint_id):
        """
        Generate PDF report for a single complaint
        
        Args:
            complaint_id: str - Complaint ID
        
        Returns:
            bytes: PDF file content
        """
        complaint = Complaint.query.get(complaint_id)
        if not complaint:
            raise ValueError(f'Complaint {complaint_id} not found')
        
        comments = ComplaintComment.query.filter_by(complaint_id=complaint_id).order_by(ComplaintComment.created_at).all()
        attachments = ComplaintAttachment.query.filter_by(complaint_id=complaint_id).all()
        
        processing_days = 0
        if complaint.closed_at and complaint.submitted_at:
            processing_days = (complaint.closed_at - complaint.submitted_at).days
        elif complaint.submitted_at:
            processing_days = (datetime.utcnow() - complaint.submitted_at).days
        
        context = {
            'complaint': {
                'complaint_id': complaint.complaint_id,
                'title': complaint.title,
                'description': complaint.description,
                'trader_name': complaint.trader.full_name if complaint.trader else '',
                'category_name': complaint.category.category_name if complaint.category else '',
                'status_name': complaint.status.status_name if complaint.status else '',
                'priority': complaint.priority,
                'submitted_at': complaint.submitted_at.strftime('%Y-%m-%d %H:%M') if complaint.submitted_at else '',
                'last_updated_at': complaint.last_updated_at.strftime('%Y-%m-%d %H:%M') if complaint.last_updated_at else '',
                'assigned_committee_member_name': complaint.assigned_committee_member.full_name if complaint.assigned_committee_member else '',
                'resolution_details': complaint.resolution_details or '',
                'closed_at': complaint.closed_at.strftime('%Y-%m-%d %H:%M') if complaint.closed_at else ''
            },
            'comments': [
                {
                    'created_at': c.created_at.strftime('%Y-%m-%d %H:%M'),
                    'author_name': c.author.full_name if c.author else '',
                    'author_role': c.author.role.role_name if c.author and c.author.role else '',
                    'comment_text': c.comment_text
                }
                for c in comments
            ],
            'attachments': [
                {
                    'file_name': a.file_name,
                    'file_type': a.file_type or '',
                    'uploaded_at': a.uploaded_at.strftime('%Y-%m-%d %H:%M') if a.uploaded_at else ''
                }
                for a in attachments
            ],
            'processing_days': processing_days
        }
        
        context = PDFService._prepare_template_context(context)
        
        html_content = render_template('pdfs/complaint_report.html', **context)
        
        pdf_file = HTML(string=html_content).write_pdf()
        
        return pdf_file
    
    @staticmethod
    def generate_monthly_report(month, year):
        """
        Generate monthly statistics PDF report
        
        Args:
            month: int - Month (1-12)
            year: int - Year
        
        Returns:
            bytes: PDF file content
        """
        from sqlalchemy import func, extract
        
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        total_complaints = Complaint.query.filter(
            Complaint.submitted_at >= start_date,
            Complaint.submitted_at < end_date
        ).count()
        
        complaints_by_status = db.session.query(
            Complaint.status_id,
            func.count(Complaint.complaint_id)
        ).filter(
            Complaint.submitted_at >= start_date,
            Complaint.submitted_at < end_date
        ).group_by(Complaint.status_id).all()
        
        status_counts = {}
        for status_id, count in complaints_by_status:
            status = db.session.query(db.Model.metadata.tables['complaint_statuses']).filter_by(status_id=status_id).first()
            if status:
                status_counts[status.status_name] = count
        
        open_complaints = status_counts.get('مفتوحة', 0)
        closed_complaints = status_counts.get('مغلقة', 0)
        in_review_complaints = status_counts.get('قيد المراجعة', 0)
        
        resolution_rate = (closed_complaints / total_complaints * 100) if total_complaints > 0 else 0
        
        closed_complaints_list = Complaint.query.filter(
            Complaint.closed_at >= start_date,
            Complaint.closed_at < end_date
        ).all()
        
        total_processing_days = sum(
            [(c.closed_at - c.submitted_at).days for c in closed_complaints_list if c.closed_at and c.submitted_at]
        )
        avg_processing_days = (total_processing_days / len(closed_complaints_list)) if closed_complaints_list else 0
        
        complaints_by_category = db.session.query(
            Complaint.category_id,
            func.count(Complaint.complaint_id)
        ).filter(
            Complaint.submitted_at >= start_date,
            Complaint.submitted_at < end_date
        ).group_by(Complaint.category_id).all()
        
        category_stats = []
        for category_id, count in complaints_by_category:
            from src.models.complaint import ComplaintCategory
            category = ComplaintCategory.query.get(category_id)
            if category:
                percentage = (count / total_complaints * 100) if total_complaints > 0 else 0
                category_stats.append({
                    'name': category.category_name,
                    'count': count,
                    'percentage': round(percentage, 2)
                })
        
        active_users = User.query.filter_by(is_active=True).count()
        
        active_subscriptions = Subscription.query.filter_by(status='active').count()
        expired_subscriptions = Subscription.query.filter_by(status='expired').count()
        
        total_subscriptions = active_subscriptions + expired_subscriptions
        renewal_rate = (active_subscriptions / total_subscriptions * 100) if total_subscriptions > 0 else 0
        
        total_payments = Payment.query.filter(
            Payment.created_at >= start_date,
            Payment.created_at < end_date
        ).count()
        
        approved_payments = Payment.query.filter(
            Payment.created_at >= start_date,
            Payment.created_at < end_date,
            Payment.status == 'approved'
        ).count()
        
        rejected_payments = Payment.query.filter(
            Payment.created_at >= start_date,
            Payment.created_at < end_date,
            Payment.status == 'rejected'
        ).count()
        
        pending_payments = Payment.query.filter(
            Payment.created_at >= start_date,
            Payment.created_at < end_date,
            Payment.status == 'pending'
        ).count()
        
        total_revenue = db.session.query(func.sum(Payment.amount)).filter(
            Payment.created_at >= start_date,
            Payment.created_at < end_date,
            Payment.status == 'approved'
        ).scalar() or 0
        
        approval_rate = (approved_payments / total_payments * 100) if total_payments > 0 else 0
        
        from src.models.complaint import Settings
        currency_setting = Settings.query.filter_by(key='currency').first()
        currency = currency_setting.value if currency_setting else 'YER'
        
        month_names = {
            1: 'يناير', 2: 'فبراير', 3: 'مارس', 4: 'أبريل',
            5: 'مايو', 6: 'يونيو', 7: 'يوليو', 8: 'أغسطس',
            9: 'سبتمبر', 10: 'أكتوبر', 11: 'نوفمبر', 12: 'ديسمبر'
        }
        
        context = {
            'month': month,
            'year': year,
            'month_name': month_names.get(month, str(month)),
            'stats': {
                'total_complaints': total_complaints,
                'open_complaints': open_complaints,
                'closed_complaints': closed_complaints,
                'in_review_complaints': in_review_complaints,
                'resolution_rate': round(resolution_rate, 2),
                'avg_processing_days': round(avg_processing_days, 2),
                'by_category': category_stats,
                'active_users': active_users,
                'active_subscriptions': active_subscriptions,
                'expired_subscriptions': expired_subscriptions,
                'renewal_rate': round(renewal_rate, 2),
                'total_payments': total_payments,
                'approved_payments': approved_payments,
                'rejected_payments': rejected_payments,
                'pending_payments': pending_payments,
                'total_revenue': round(total_revenue, 2),
                'currency': currency,
                'approval_rate': round(approval_rate, 2),
                'key_events': [],
                'recommendations': [
                    'مراقبة الشكاوى المفتوحة وضمان المتابعة السريعة',
                    'تحسين معدل الحل من خلال تخصيص الموارد بشكل أفضل',
                    'متابعة الاشتراكات المنتهية وتشجيع التجديد',
                    'تحسين عملية مراجعة المدفوعات لتقليل وقت الانتظار'
                ]
            },
            'chart_path': None
        }
        
        context = PDFService._prepare_template_context(context)
        
        html_content = render_template('pdfs/monthly_report.html', **context)
        
        pdf_file = HTML(string=html_content).write_pdf()
        
        return pdf_file
    
    @staticmethod
    def generate_payment_receipt(payment_id):
        """
        Generate payment receipt PDF
        
        Args:
            payment_id: str - Payment ID
        
        Returns:
            bytes: PDF file content
        """
        payment = Payment.query.get(payment_id)
        if not payment:
            raise ValueError(f'Payment {payment_id} not found')
        
        subscription = None
        if payment.status == 'approved':
            subscription = Subscription.query.filter_by(user_id=payment.user_id).order_by(Subscription.created_at.desc()).first()
        
        context = {
            'payment': {
                'payment_id': payment.payment_id,
                'user_name': payment.user.full_name if payment.user else '',
                'sender_name': payment.sender_name,
                'sender_phone': payment.sender_phone,
                'method_name': payment.payment_method.name if payment.payment_method else '',
                'amount': payment.amount,
                'currency': payment.currency,
                'transaction_reference': payment.transaction_reference or '',
                'payment_date': payment.payment_date.strftime('%Y-%m-%d %H:%M') if payment.payment_date else '',
                'status': payment.status,
                'reviewed_by_name': payment.reviewed_by.full_name if payment.reviewed_by else '',
                'review_notes': payment.review_notes or '',
                'reviewed_at': payment.reviewed_at.strftime('%Y-%m-%d %H:%M') if payment.reviewed_at else ''
            },
            'subscription_info': None
        }
        
        if subscription:
            context['subscription_info'] = {
                'plan': subscription.plan,
                'start_date': subscription.start_date.strftime('%Y-%m-%d') if subscription.start_date else '',
                'end_date': subscription.end_date.strftime('%Y-%m-%d') if subscription.end_date else ''
            }
        
        context = PDFService._prepare_template_context(context)
        
        html_content = render_template('pdfs/payment_receipt.html', **context)
        
        pdf_file = HTML(string=html_content).write_pdf()
        
        return pdf_file
