# type: ignore
import os
import subprocess
import hashlib
import gzip
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from src.models.complaint import db, BackupLog
from src.services.notification_service import NotificationService

class BackupService:
    """Service for automated PostgreSQL database backups"""
    
    def __init__(self):
        self.backup_dir = os.environ.get('BACKUP_DIRECTORY', os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'backups'
        ))
        self.retention_days = int(os.environ.get('BACKUP_RETENTION_DAYS', 30))
        self.database_url = os.environ.get('DATABASE_URL', '')
        
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def _parse_database_url(self):
        """Parse DATABASE_URL into connection parameters"""
        if not self.database_url:
            raise ValueError('DATABASE_URL environment variable not set')
        
        if self.database_url.startswith('postgres://') or self.database_url.startswith('postgresql://'):
            url = self.database_url.replace('postgres://', 'postgresql://')
            
            from urllib.parse import urlparse
            parsed = urlparse(url)
            
            return {
                'host': parsed.hostname,
                'port': parsed.port or 5432,
                'database': parsed.path.lstrip('/'),
                'username': parsed.username,
                'password': parsed.password
            }
        else:
            raise ValueError('DATABASE_URL must be a PostgreSQL connection string')
    
    def _calculate_checksum(self, file_path):
        """Calculate SHA256 checksum of a file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def create_backup(self):
        """
        Create PostgreSQL backup using pg_dump
        
        Returns:
            dict: Backup result with status and details
        """
        try:
            db_params = self._parse_database_url()
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f'backup_{timestamp}.sql'
            backup_path = os.path.join(self.backup_dir, backup_filename)
            compressed_filename = f'{backup_filename}.gz'
            compressed_path = os.path.join(self.backup_dir, compressed_filename)
            
            env = os.environ.copy()
            env['PGPASSWORD'] = db_params['password']
            
            pg_dump_cmd = [
                'pg_dump',
                '-h', db_params['host'],
                '-p', str(db_params['port']),
                '-U', db_params['username'],
                '-d', db_params['database'],
                '-F', 'p',
                '-f', backup_path,
                '--no-owner',
                '--no-acl'
            ]
            
            result = subprocess.run(
                pg_dump_cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.returncode != 0:
                error_msg = f'pg_dump failed: {result.stderr}'
                self._log_backup(compressed_filename, 0, 'failed', error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }
            
            with open(backup_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            os.remove(backup_path)
            
            file_size = os.path.getsize(compressed_path)
            checksum = self._calculate_checksum(compressed_path)
            
            backup_log = self._log_backup(compressed_filename, file_size, 'success', None, checksum)
            
            self._notify_backup_success(compressed_filename, file_size)
            
            return {
                'success': True,
                'filename': compressed_filename,
                'path': compressed_path,
                'size_bytes': file_size,
                'checksum': checksum,
                'log_id': backup_log.id
            }
        
        except subprocess.TimeoutExpired:
            error_msg = 'Backup timed out after 10 minutes'
            self._log_backup('timeout', 0, 'failed', error_msg)
            self._notify_backup_failure(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
        
        except Exception as e:
            error_msg = f'Backup failed: {str(e)}'
            self._log_backup('error', 0, 'failed', error_msg)
            self._notify_backup_failure(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def _log_backup(self, filename, size_bytes, status, error_message=None, checksum=None):
        """Log backup to database"""
        try:
            backup_log = BackupLog(
                filename=filename,
                size_bytes=size_bytes,
                status=status,
                error_message=error_message,
                checksum=checksum
            )
            db.session.add(backup_log)
            db.session.commit()
            return backup_log
        except Exception as e:
            db.session.rollback()
            print(f'Failed to log backup: {str(e)}')
            return None
    
    def _notify_backup_success(self, filename, size_bytes):
        """Notify admin about successful backup"""
        try:
            from src.models.complaint import User, Role
            
            admin_role = Role.query.filter_by(role_name='Higher Committee').first()
            if admin_role:
                admins = User.query.filter_by(role_id=admin_role.role_id, is_active=True).all()
                
                size_mb = size_bytes / (1024 * 1024)
                
                for admin in admins:
                    try:
                        NotificationService.queue_notification(
                            user=admin,
                            notification_type='backup_success',
                            message=f'تم إنشاء نسخة احتياطية بنجاح: {filename} (الحجم: {size_mb:.2f} ميجابايت)',
                            channel='in_app',
                            filename=filename,
                            size_mb=f'{size_mb:.2f}'
                        )
                    except Exception as e:
                        print(f'Failed to notify admin {admin.user_id}: {str(e)}')
        except Exception as e:
            print(f'Failed to send backup success notifications: {str(e)}')
    
    def _notify_backup_failure(self, error_message):
        """Notify admin about backup failure"""
        try:
            from src.models.complaint import User, Role
            
            admin_role = Role.query.filter_by(role_name='Higher Committee').first()
            if admin_role:
                admins = User.query.filter_by(role_id=admin_role.role_id, is_active=True).all()
                
                for admin in admins:
                    try:
                        NotificationService.queue_notification(
                            user=admin,
                            notification_type='backup_failure',
                            message=f'فشل إنشاء النسخة الاحتياطية: {error_message}',
                            channel='email',
                            error=error_message
                        )
                    except Exception as e:
                        print(f'Failed to notify admin {admin.user_id}: {str(e)}')
        except Exception as e:
            print(f'Failed to send backup failure notifications: {str(e)}')
    
    def cleanup_old_backups(self):
        """
        Delete backups older than retention period
        Retention policy:
        - Daily backups: 7 days
        - Weekly backups: 30 days
        - Monthly backups: 1 year
        
        Returns:
            dict: Cleanup result
        """
        try:
            now = datetime.now()
            deleted_count = 0
            kept_count = 0
            
            backup_files = sorted(
                Path(self.backup_dir).glob('backup_*.sql.gz'),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            
            monthly_backups = {}
            weekly_backups = {}
            
            for backup_file in backup_files:
                file_mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)
                age_days = (now - file_mtime).days
                
                is_monthly = file_mtime.day == 1
                week_key = f'{file_mtime.year}-W{file_mtime.isocalendar()[1]}'
                
                keep = False
                reason = ''
                
                if is_monthly and age_days <= 365:
                    month_key = f'{file_mtime.year}-{file_mtime.month:02d}'
                    if month_key not in monthly_backups:
                        monthly_backups[month_key] = backup_file
                        keep = True
                        reason = 'monthly'
                
                elif week_key not in weekly_backups and age_days <= 30:
                    weekly_backups[week_key] = backup_file
                    keep = True
                    reason = 'weekly'
                
                elif age_days <= 7:
                    keep = True
                    reason = 'daily'
                
                if not keep:
                    try:
                        backup_file.unlink()
                        deleted_count += 1
                        
                        BackupLog.query.filter_by(filename=backup_file.name).update({'status': 'deleted'})
                    except Exception as e:
                        print(f'Failed to delete {backup_file}: {str(e)}')
                else:
                    kept_count += 1
            
            db.session.commit()
            
            return {
                'success': True,
                'deleted_count': deleted_count,
                'kept_count': kept_count
            }
        
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': str(e)
            }
    
    def list_backups(self):
        """
        List all available backups with timestamps and sizes
        
        Returns:
            list: List of backup information dictionaries
        """
        try:
            backups = []
            
            for backup_file in sorted(Path(self.backup_dir).glob('backup_*.sql.gz'), reverse=True):
                file_stats = backup_file.stat()
                
                backup_log = BackupLog.query.filter_by(filename=backup_file.name).first()
                
                backups.append({
                    'filename': backup_file.name,
                    'path': str(backup_file),
                    'size_bytes': file_stats.st_size,
                    'size_mb': file_stats.st_size / (1024 * 1024),
                    'created_at': datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
                    'status': backup_log.status if backup_log else 'unknown',
                    'checksum': backup_log.checksum if backup_log else None
                })
            
            return backups
        
        except Exception as e:
            print(f'Failed to list backups: {str(e)}')
            return []
    
    def upload_to_storage(self, backup_file):
        """
        Upload backup to cloud storage (optional, requires S3 credentials)
        
        Args:
            backup_file: str - Path to backup file
        
        Returns:
            dict: Upload result
        """
        s3_bucket = os.environ.get('S3_BUCKET')
        s3_access_key = os.environ.get('S3_ACCESS_KEY')
        s3_secret_key = os.environ.get('S3_SECRET_KEY')
        
        if not all([s3_bucket, s3_access_key, s3_secret_key]):
            return {
                'success': False,
                'error': 'S3 credentials not configured'
            }
        
        try:
            import boto3
            
            s3_client = boto3.client(
                's3',
                aws_access_key_id=s3_access_key,
                aws_secret_access_key=s3_secret_key
            )
            
            filename = os.path.basename(backup_file)
            s3_key = f'backups/{filename}'
            
            s3_client.upload_file(backup_file, s3_bucket, s3_key)
            
            return {
                'success': True,
                'bucket': s3_bucket,
                'key': s3_key
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': f'S3 upload failed: {str(e)}'
            }
