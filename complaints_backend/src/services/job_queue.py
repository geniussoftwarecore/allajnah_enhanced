import os
from datetime import datetime, timedelta
from redis import Redis
from rq import Queue
from flask import current_app
from src.database.db import db
from src.models.complaint import User, Subscription, Settings, Notification

redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

try:
    redis_conn = Redis.from_url(redis_url)
    redis_conn.ping()
    use_redis = True
except Exception as e:
    redis_conn = None
    use_redis = False
    print(f'Redis connection failed, using in-memory fallback: {str(e)}')

if use_redis:
    notification_queue = Queue('notifications', connection=redis_conn, default_timeout=300)
    maintenance_queue = Queue('maintenance', connection=redis_conn, default_timeout=600)
else:
    notification_queue = None
    maintenance_queue = None


def send_notification_job(user_id, notification_type, message, channel='in_app', **context):
    """
    Background job to send notification
    
    Args:
        user_id: User ID
        notification_type: Type of notification
        message: Notification message
        channel: Notification channel ('in_app', 'email', 'sms', 'all')
        **context: Additional context for templates
    """
    from src.services.notification_service import NotificationService
    from flask import Flask
    
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///database/app.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', os.environ.get('MAIL_USERNAME', ''))
    
    from src.services.notification_service import mail
    mail.init_app(app)
    
    with app.app_context():
        db.init_app(app)
        
        try:
            user = User.query.get(user_id)
            if not user:
                print(f'User {user_id} not found for notification')
                return {'success': False, 'error': 'User not found'}
            
            notification = NotificationService.queue_notification(
                user=user,
                notification_type=notification_type,
                message=message,
                channel=channel,
                **context
            )
            
            print(f'Notification sent: {notification.notification_id}')
            return {'success': True, 'notification_id': notification.notification_id}
            
        except Exception as e:
            print(f'Failed to send notification: {str(e)}')
            return {'success': False, 'error': str(e)}


def check_renewals_job():
    """
    Background job to check subscriptions and send renewal reminders
    Runs daily to check for subscriptions expiring in 14, 7, or 3 days
    """
    from src.services.notification_service import NotificationService
    from flask import Flask
    
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///database/app.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', os.environ.get('MAIL_USERNAME', ''))
    
    from src.services.notification_service import mail
    mail.init_app(app)
    
    with app.app_context():
        db.init_app(app)
        
        try:
            now = datetime.utcnow()
            reminders_sent = 0
            
            active_subscriptions = Subscription.query.filter_by(status='active').all()
            
            for subscription in active_subscriptions:
                days_remaining = (subscription.end_date - now).days
                user = User.query.get(subscription.user_id)
                
                if not user:
                    continue
                
                if days_remaining == 14 and not subscription.notified_14d:
                    NotificationService.queue_notification(
                        user=user,
                        notification_type='renewal_reminder_14d',
                        message=f'اشتراكك سينتهي خلال 14 يوم. يرجى تجديد الاشتراك.',
                        channel='email',
                        end_date=subscription.end_date.strftime('%Y-%m-%d'),
                        days_remaining=14
                    )
                    subscription.notified_14d = True
                    reminders_sent += 1
                
                elif days_remaining == 7 and not subscription.notified_7d:
                    NotificationService.queue_notification(
                        user=user,
                        notification_type='renewal_reminder_7d',
                        message=f'اشتراكك سينتهي خلال 7 أيام. يرجى تجديد الاشتراك.',
                        channel='email',
                        end_date=subscription.end_date.strftime('%Y-%m-%d'),
                        days_remaining=7
                    )
                    subscription.notified_7d = True
                    reminders_sent += 1
                
                elif days_remaining == 3 and not subscription.notified_3d:
                    NotificationService.queue_notification(
                        user=user,
                        notification_type='renewal_reminder_3d',
                        message=f'تحذير: اشتراكك سينتهي خلال 3 أيام. يرجى تجديد الاشتراك فوراً.',
                        channel='all',
                        end_date=subscription.end_date.strftime('%Y-%m-%d'),
                        days_remaining=3
                    )
                    subscription.notified_3d = True
                    reminders_sent += 1
            
            db.session.commit()
            print(f'Renewal reminders sent: {reminders_sent}')
            return {'success': True, 'reminders_sent': reminders_sent}
            
        except Exception as e:
            db.session.rollback()
            print(f'Failed to check renewals: {str(e)}')
            return {'success': False, 'error': str(e)}


def cleanup_files_job(days_old=30):
    """
    Background job to cleanup old files
    
    Args:
        days_old: Delete files older than this many days (default 30)
    """
    import shutil
    from pathlib import Path
    
    try:
        uploads_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads', 'receipts')
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        deleted_count = 0
        
        if not os.path.exists(uploads_dir):
            return {'success': True, 'deleted_count': 0}
        
        for file_path in Path(uploads_dir).glob('*'):
            if file_path.is_file():
                file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_mtime < cutoff_date:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                    except Exception as e:
                        print(f'Failed to delete {file_path}: {str(e)}')
        
        print(f'Cleaned up {deleted_count} old files')
        return {'success': True, 'deleted_count': deleted_count}
        
    except Exception as e:
        print(f'Failed to cleanup files: {str(e)}')
        return {'success': False, 'error': str(e)}


def enqueue_notification(user_id, notification_type, message, channel='in_app', **context):
    """Helper to enqueue notification job if Redis available, otherwise run synchronously"""
    if use_redis and notification_queue:
        try:
            job = notification_queue.enqueue(
                send_notification_job,
                user_id=user_id,
                notification_type=notification_type,
                message=message,
                channel=channel,
                **context
            )
            return {'success': True, 'job_id': job.id}
        except Exception as e:
            current_app.logger.error(f'Failed to enqueue notification: {str(e)}')
    
    return send_notification_job(user_id, notification_type, message, channel, **context)


def enqueue_renewals_check():
    """Helper to enqueue renewals check job"""
    if use_redis and maintenance_queue:
        try:
            job = maintenance_queue.enqueue(check_renewals_job)
            return {'success': True, 'job_id': job.id}
        except Exception as e:
            print(f'Failed to enqueue renewals check: {str(e)}')
    
    return check_renewals_job()


def enqueue_cleanup(days_old=30):
    """Helper to enqueue cleanup job"""
    if use_redis and maintenance_queue:
        try:
            job = maintenance_queue.enqueue(cleanup_files_job, days_old=days_old)
            return {'success': True, 'job_id': job.id}
        except Exception as e:
            print(f'Failed to enqueue cleanup: {str(e)}')
    
    return cleanup_files_job(days_old)
