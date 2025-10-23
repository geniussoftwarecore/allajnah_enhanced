import os
from datetime import datetime
from flask import current_app
from flask_mail import Mail, Message
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import arabic_reshaper
from bidi.algorithm import get_display
from src.database.db import db
from src.models.complaint import Notification

mail = Mail()

class NotificationService:
    
    @staticmethod
    def _reshape_arabic(text):
        """Reshape Arabic text for proper RTL display"""
        try:
            reshaped_text = arabic_reshaper.reshape(text)
            return get_display(reshaped_text)
        except Exception as e:
            current_app.logger.warning(f'Arabic reshaping failed: {str(e)}')
            return text
    
    @staticmethod
    def send_email(user, subject, template_name, **context):
        """
        Send email notification to user
        
        Args:
            user: User model instance
            subject: Email subject
            template_name: Template filename (without .html)
            **context: Template context variables
            
        Returns:
            dict: {'success': bool, 'error': str or None}
        """
        try:
            if not all([
                os.environ.get('MAIL_SERVER'),
                os.environ.get('MAIL_USERNAME'),
                os.environ.get('MAIL_PASSWORD')
            ]):
                current_app.logger.warning('Email configuration missing - email not sent')
                return {'success': False, 'error': 'Email configuration missing'}
            
            if not user.email:
                return {'success': False, 'error': 'User has no email address'}
            
            msg = Message(
                subject=subject,
                sender=os.environ.get('MAIL_DEFAULT_SENDER', os.environ.get('MAIL_USERNAME')),
                recipients=[user.email]
            )
            
            template_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'templates',
                'emails',
                f'{template_name}.html'
            )
            
            if os.path.exists(template_path):
                with open(template_path, 'r', encoding='utf-8') as f:
                    template_content = f.read()
                
                for key, value in context.items():
                    template_content = template_content.replace(f'{{{{{key}}}}}', str(value))
                
                msg.html = template_content
            else:
                msg.html = context.get('body', '')
            
            mail.send(msg)
            current_app.logger.info(f'Email sent to {user.email} - {subject}')
            return {'success': True, 'error': None}
            
        except Exception as e:
            error_msg = f'Failed to send email: {str(e)}'
            current_app.logger.error(error_msg)
            return {'success': False, 'error': error_msg}
    
    @staticmethod
    def send_sms(user, message):
        """
        Send SMS notification to user (critical notifications only)
        
        Args:
            user: User model instance
            message: SMS text message
            
        Returns:
            dict: {'success': bool, 'error': str or None}
        """
        try:
            account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
            auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
            from_phone = os.environ.get('TWILIO_PHONE_NUMBER')
            
            if not all([account_sid, auth_token, from_phone]):
                current_app.logger.warning('Twilio configuration missing - SMS not sent')
                return {'success': False, 'error': 'SMS configuration missing'}
            
            if not user.phone_number:
                return {'success': False, 'error': 'User has no phone number'}
            
            client = Client(account_sid, auth_token)
            
            reshaped_message = NotificationService._reshape_arabic(message)
            
            twilio_message = client.messages.create(
                body=reshaped_message,
                from_=from_phone,
                to=user.phone_number
            )
            
            current_app.logger.info(f'SMS sent to {user.phone_number} - SID: {twilio_message.sid}')
            return {'success': True, 'error': None}
            
        except TwilioRestException as e:
            error_msg = f'Twilio error: {str(e)}'
            current_app.logger.error(error_msg)
            return {'success': False, 'error': error_msg}
        except Exception as e:
            error_msg = f'Failed to send SMS: {str(e)}'
            current_app.logger.error(error_msg)
            return {'success': False, 'error': error_msg}
    
    @staticmethod
    def queue_notification(user, notification_type, message, channel='in_app', complaint_id=None, **context):
        """
        Queue notification and optionally send via email/SMS
        
        Args:
            user: User model instance
            notification_type: Type of notification (e.g., 'payment_approved', 'renewal_reminder')
            message: Notification message
            channel: 'in_app', 'email', 'sms', or 'all'
            complaint_id: Optional complaint ID
            **context: Additional context for email templates
            
        Returns:
            Notification model instance
        """
        try:
            notification = Notification(
                user_id=user.user_id,
                complaint_id=complaint_id,
                message=message,
                type=notification_type,
                channel=channel,
                status='pending'
            )
            
            db.session.add(notification)
            db.session.flush()
            
            if channel in ['email', 'all']:
                result = NotificationService._send_email_for_type(
                    user, notification_type, **context
                )
                if result['success']:
                    notification.status = 'sent'
                    notification.sent_at = datetime.utcnow()
                else:
                    notification.status = 'failed'
                    notification.error_message = result['error']
            
            if channel in ['sms', 'all']:
                sms_message = NotificationService._get_sms_template(notification_type, **context)
                if sms_message:
                    result = NotificationService.send_sms(user, sms_message)
                    if result['success']:
                        notification.status = 'sent'
                        notification.sent_at = datetime.utcnow()
                    else:
                        if notification.status != 'sent':
                            notification.status = 'failed'
                        notification.error_message = result['error']
            
            if channel == 'in_app':
                notification.status = 'sent'
                notification.sent_at = datetime.utcnow()
            
            db.session.commit()
            return notification
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Failed to queue notification: {str(e)}')
            raise
    
    @staticmethod
    def _send_email_for_type(user, notification_type, **context):
        """Send email based on notification type"""
        
        email_configs = {
            'renewal_reminder_14d': {
                'subject': 'تذكير: اشتراكك سينتهي خلال 14 يوم',
                'template': 'renewal_reminder',
                'days': 14
            },
            'renewal_reminder_7d': {
                'subject': 'تذكير: اشتراكك سينتهي خلال 7 أيام',
                'template': 'renewal_reminder',
                'days': 7
            },
            'renewal_reminder_3d': {
                'subject': 'تحذير: اشتراكك سينتهي خلال 3 أيام',
                'template': 'renewal_reminder',
                'days': 3
            },
            'payment_approved': {
                'subject': 'تم اعتماد دفعتك بنجاح',
                'template': 'payment_approved'
            },
            'payment_rejected': {
                'subject': 'تم رفض دفعتك',
                'template': 'payment_rejected'
            },
            'complaint_status_changed': {
                'subject': 'تحديث حالة الشكوى',
                'template': 'complaint_status_changed'
            },
            'welcome': {
                'subject': 'مرحباً بك في نظام الشكاوى الإلكتروني',
                'template': 'welcome'
            }
        }
        
        config = email_configs.get(notification_type)
        if not config:
            return {'success': False, 'error': 'Unknown notification type'}
        
        template_context = {
            'user_name': user.full_name,
            **context
        }
        
        if notification_type.startswith('renewal_reminder'):
            template_context['days_remaining'] = config['days']
        
        return NotificationService.send_email(
            user,
            config['subject'],
            config['template'],
            **template_context
        )
    
    @staticmethod
    def _get_sms_template(notification_type, **context):
        """Get SMS message template for critical notifications only"""
        
        sms_templates = {
            'payment_approved': f'تم اعتماد دفعتك بنجاح. تم تفعيل اشتراكك السنوي.',
            'renewal_reminder_3d': f'تحذير: اشتراكك سينتهي خلال 3 أيام. يرجى تجديد الاشتراك.',
        }
        
        return sms_templates.get(notification_type)
