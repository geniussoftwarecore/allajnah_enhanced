# type: ignore
from flask import Blueprint, request, jsonify, send_file, current_app
from datetime import datetime, timedelta
from functools import wraps
import os
import io
from src.routes.auth import token_required, role_required, rate_limit
from src.services.export_service import ExportService
from src.services.pdf_service import PDFService
from src.models.complaint import db, Export
from src.services.job_queue import use_redis, notification_queue

export_bp = Blueprint('export', __name__)

def track_export(export_type):
    """Decorator to track export generation"""
    def decorator(f):
        @wraps(f)
        def decorated(current_user, *args, **kwargs):
            result = f(current_user, *args, **kwargs)
            
            try:
                if isinstance(result, tuple) and len(result) >= 2:
                    response, status_code = result[:2]
                else:
                    response = result
                    status_code = 200
                
                if status_code == 200:
                    filename = kwargs.get('filename', f'{export_type}_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
                    
                    export_record = Export(
                        user_id=current_user.user_id,
                        export_type=export_type,
                        filename=filename,
                        status='completed',
                        expires_at=datetime.utcnow() + timedelta(hours=int(os.environ.get('EXPORT_EXPIRY_HOURS', 24)))
                    )
                    db.session.add(export_record)
                    db.session.commit()
            except Exception as e:
                current_app.logger.error(f'Error tracking export: {str(e)}')
            
            return result
        return decorated
    return decorator


@export_bp.route('/export/complaints/excel', methods=['GET'])
@token_required
@rate_limit('10 per hour')
@track_export('complaints_excel')
def export_complaints_excel(current_user):
    """Export complaints to Excel"""
    try:
        filters = {}
        
        if request.args.get('start_date'):
            try:
                filters['start_date'] = datetime.strptime(request.args.get('start_date'), '%Y-%m-%d')
            except ValueError:
                return jsonify({'error': 'تنسيق تاريخ البدء غير صالح. استخدم YYYY-MM-DD'}), 400
        
        if request.args.get('end_date'):
            try:
                filters['end_date'] = datetime.strptime(request.args.get('end_date'), '%Y-%m-%d')
            except ValueError:
                return jsonify({'error': 'تنسيق تاريخ النهاية غير صالح. استخدم YYYY-MM-DD'}), 400
        
        if request.args.get('status_id'):
            filters['status_id'] = int(request.args.get('status_id'))
        
        if request.args.get('category_id'):
            filters['category_id'] = int(request.args.get('category_id'))
        
        if current_user.role.role_name == 'Trader':
            filters['trader_id'] = current_user.user_id
        elif request.args.get('trader_id'):
            filters['trader_id'] = request.args.get('trader_id')
        
        file_path = ExportService.export_complaints_to_excel(filters)
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=os.path.basename(file_path),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    
    except Exception as e:
        current_app.logger.error(f'Error exporting complaints to Excel: {str(e)}')
        return jsonify({'error': f'فشل تصدير الشكاوى: {str(e)}'}), 500


@export_bp.route('/export/payments/excel', methods=['GET'])
@token_required
@rate_limit('10 per hour')
@track_export('payments_excel')
def export_payments_excel(current_user):
    """Export payments to Excel"""
    try:
        filters = {}
        
        if request.args.get('start_date'):
            try:
                filters['start_date'] = datetime.strptime(request.args.get('start_date'), '%Y-%m-%d')
            except ValueError:
                return jsonify({'error': 'تنسيق تاريخ البدء غير صالح. استخدم YYYY-MM-DD'}), 400
        
        if request.args.get('end_date'):
            try:
                filters['end_date'] = datetime.strptime(request.args.get('end_date'), '%Y-%m-%d')
            except ValueError:
                return jsonify({'error': 'تنسيق تاريخ النهاية غير صالح. استخدم YYYY-MM-DD'}), 400
        
        if request.args.get('status'):
            filters['status'] = request.args.get('status')
        
        if current_user.role.role_name == 'Trader':
            filters['user_id'] = current_user.user_id
        elif request.args.get('user_id'):
            filters['user_id'] = request.args.get('user_id')
        
        file_path = ExportService.export_payments_to_excel(filters)
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=os.path.basename(file_path),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    
    except Exception as e:
        current_app.logger.error(f'Error exporting payments to Excel: {str(e)}')
        return jsonify({'error': f'فشل تصدير المدفوعات: {str(e)}'}), 500


@export_bp.route('/export/users/excel', methods=['GET'])
@token_required
@role_required(['Higher Committee'])
@rate_limit('5 per hour')
@track_export('users_excel')
def export_users_excel(current_user):
    """Export users to Excel (admin only)"""
    try:
        role_filter = request.args.get('role')
        
        if role_filter:
            role_filter = role_filter.split(',')
        
        file_path = ExportService.export_users_to_excel(role_filter)
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=os.path.basename(file_path),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    
    except Exception as e:
        current_app.logger.error(f'Error exporting users to Excel: {str(e)}')
        return jsonify({'error': f'فشل تصدير المستخدمين: {str(e)}'}), 500


@export_bp.route('/export/subscriptions/excel', methods=['GET'])
@token_required
@role_required(['Higher Committee'])
@rate_limit('5 per hour')
@track_export('subscriptions_excel')
def export_subscriptions_excel(current_user):
    """Export subscriptions to Excel (admin only)"""
    try:
        file_path = ExportService.export_subscriptions_to_excel()
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=os.path.basename(file_path),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    
    except Exception as e:
        current_app.logger.error(f'Error exporting subscriptions to Excel: {str(e)}')
        return jsonify({'error': f'فشل تصدير الاشتراكات: {str(e)}'}), 500


@export_bp.route('/export/complaint/<complaint_id>/pdf', methods=['GET'])
@token_required
@rate_limit('20 per hour')
@track_export('complaint_pdf')
def export_complaint_pdf(current_user, complaint_id):
    """Download complaint PDF report"""
    try:
        from src.models.complaint import Complaint
        
        complaint = Complaint.query.get(complaint_id)
        if not complaint:
            return jsonify({'error': 'الشكوى غير موجودة'}), 404
        
        if current_user.role.role_name == 'Trader' and complaint.trader_id != current_user.user_id:
            return jsonify({'error': 'ليس لديك صلاحية لتصدير هذه الشكوى'}), 403
        
        pdf_content = PDFService.generate_complaint_report(complaint_id)
        
        pdf_buffer = io.BytesIO(pdf_content)
        pdf_buffer.seek(0)
        
        filename = f'complaint_report_{complaint_id}_{datetime.now().strftime("%Y%m%d")}.pdf'
        
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
    
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        current_app.logger.error(f'Error generating complaint PDF: {str(e)}')
        return jsonify({'error': f'فشل إنشاء تقرير PDF: {str(e)}'}), 500


@export_bp.route('/export/monthly-report/<int:year>/<int:month>/pdf', methods=['GET'])
@token_required
@role_required(['Higher Committee', 'Technical Committee'])
@rate_limit('5 per hour')
@track_export('monthly_report_pdf')
def export_monthly_report_pdf(current_user, year, month):
    """Download monthly report PDF (admin/committee only)"""
    try:
        if month < 1 or month > 12:
            return jsonify({'error': 'الشهر يجب أن يكون بين 1 و 12'}), 400
        
        if year < 2020 or year > datetime.now().year + 1:
            return jsonify({'error': 'السنة غير صالحة'}), 400
        
        pdf_content = PDFService.generate_monthly_report(month, year)
        
        pdf_buffer = io.BytesIO(pdf_content)
        pdf_buffer.seek(0)
        
        filename = f'monthly_report_{year}_{month:02d}_{datetime.now().strftime("%Y%m%d")}.pdf'
        
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
    
    except Exception as e:
        current_app.logger.error(f'Error generating monthly report PDF: {str(e)}')
        return jsonify({'error': f'فشل إنشاء التقرير الشهري: {str(e)}'}), 500


@export_bp.route('/export/payment/<payment_id>/receipt/pdf', methods=['GET'])
@token_required
@rate_limit('20 per hour')
@track_export('payment_receipt_pdf')
def export_payment_receipt_pdf(current_user, payment_id):
    """Download payment receipt PDF"""
    try:
        from src.models.complaint import Payment
        
        payment = Payment.query.get(payment_id)
        if not payment:
            return jsonify({'error': 'الدفع غير موجود'}), 404
        
        if current_user.role.role_name == 'Trader' and payment.user_id != current_user.user_id:
            return jsonify({'error': 'ليس لديك صلاحية لتصدير إيصال هذا الدفع'}), 403
        
        pdf_content = PDFService.generate_payment_receipt(payment_id)
        
        pdf_buffer = io.BytesIO(pdf_content)
        pdf_buffer.seek(0)
        
        filename = f'payment_receipt_{payment_id}_{datetime.now().strftime("%Y%m%d")}.pdf'
        
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
    
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        current_app.logger.error(f'Error generating payment receipt PDF: {str(e)}')
        return jsonify({'error': f'فشل إنشاء إيصال الدفع: {str(e)}'}), 500


@export_bp.route('/export/history', methods=['GET'])
@token_required
@rate_limit('30 per hour')
def get_export_history(current_user):
    """Get user's export history"""
    try:
        if current_user.role.role_name == 'Higher Committee':
            exports = Export.query.order_by(Export.created_at.desc()).limit(50).all()
        else:
            exports = Export.query.filter_by(user_id=current_user.user_id).order_by(Export.created_at.desc()).limit(20).all()
        
        return jsonify({
            'exports': [export.to_dict() for export in exports]
        }), 200
    
    except Exception as e:
        current_app.logger.error(f'Error fetching export history: {str(e)}')
        return jsonify({'error': 'فشل جلب سجل التصدير'}), 500
