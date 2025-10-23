import os
import uuid
import magic
import redis
import json
from datetime import datetime, timedelta
from typing import Tuple, Optional
from werkzeug.utils import secure_filename
from flask import current_app

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg'}
ALLOWED_MIME_TYPES = {
    'image/png',
    'image/jpeg',
    'image/jpg'
}

MAX_FILE_SIZE = 5 * 1024 * 1024

def validate_file_extension(filename):
    """التحقق من امتداد الملف"""
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in ALLOWED_IMAGE_EXTENSIONS

def validate_mime_type(file_path):
    """التحقق من نوع MIME الفعلي للملف"""
    try:
        mime = magic.Magic(mime=True)
        file_mime = mime.from_file(file_path)
        return file_mime in ALLOWED_MIME_TYPES
    except Exception as e:
        current_app.logger.error(f'خطأ في التحقق من MIME: {str(e)}')
        return False

def validate_file_size(file):
    """التحقق من حجم الملف"""
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    return size <= MAX_FILE_SIZE

def generate_secure_filename(original_filename):
    """توليد اسم ملف آمن وعشوائي"""
    if not original_filename or '.' not in original_filename:
        raise ValueError('اسم ملف غير صالح')
    
    ext = original_filename.rsplit('.', 1)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError(f'امتداد الملف غير مسموح. الامتدادات المسموحة: {", ".join(ALLOWED_IMAGE_EXTENSIONS)}')
    
    random_name = str(uuid.uuid4())
    safe_filename = f"{random_name}.{ext}"
    return secure_filename(safe_filename)

def validate_payment_data(data):
    """التحقق القوي من بيانات الدفع"""
    errors = []
    
    required_fields = {
        'method_id': 'معرف طريقة الدفع',
        'sender_name': 'اسم المُرسل',
        'sender_phone': 'رقم الهاتف',
        'amount': 'المبلغ',
        'payment_date': 'تاريخ الدفع'
    }
    
    for field, label in required_fields.items():
        if field not in data or not data[field]:
            errors.append(f'{label} مطلوب')
    
    if 'sender_name' in data:
        name = str(data['sender_name']).strip()
        if len(name) < 3:
            errors.append('اسم المُرسل يجب أن يكون 3 أحرف على الأقل')
        if len(name) > 255:
            errors.append('اسم المُرسل طويل جداً (الحد الأقصى 255 حرف)')
    
    if 'sender_phone' in data:
        phone = str(data['sender_phone']).strip()
        if len(phone) < 9:
            errors.append('رقم الهاتف غير صالح (9 أرقام على الأقل)')
        if len(phone) > 15:
            errors.append('رقم الهاتف طويل جداً (الحد الأقصى 15 رقم)')
        if not phone.replace('+', '').replace(' ', '').isdigit():
            errors.append('رقم الهاتف يجب أن يحتوي على أرقام فقط')
    
    if 'amount' in data:
        try:
            amount = float(data['amount'])
            if amount <= 0:
                errors.append('المبلغ يجب أن يكون أكبر من صفر')
            if amount > 10000000:
                errors.append('المبلغ كبير جداً')
        except (ValueError, TypeError):
            errors.append('المبلغ غير صالح')
    
    if 'transaction_reference' in data and data['transaction_reference']:
        ref = str(data['transaction_reference']).strip()
        if len(ref) > 255:
            errors.append('مرجع العملية طويل جداً (الحد الأقصى 255 حرف)')
    
    return errors

def sanitize_filename(filename):
    """تنظيف اسم الملف من المحارف الخطرة"""
    if not filename:
        return None
    
    filename = filename.strip()
    dangerous_chars = ['..', '/', '\\', '\0', '\n', '\r', '\t']
    
    for char in dangerous_chars:
        filename = filename.replace(char, '')
    
    return secure_filename(filename)

def validate_and_save_file(file, upload_folder):
    """
    التحقق الشامل من الملف وحفظه بشكل آمن
    
    Returns:
        tuple: (success: bool, result: str or dict)
    """
    if not file or file.filename == '':
        return False, {'error': 'لم يتم اختيار ملف'}
    
    if not validate_file_extension(file.filename):
        return False, {'error': f'نوع الملف غير مسموح. الامتدادات المسموحة: {", ".join(ALLOWED_IMAGE_EXTENSIONS)}'}
    
    if not validate_file_size(file):
        return False, {'error': f'حجم الملف يجب أن يكون أقل من {MAX_FILE_SIZE / (1024*1024):.0f} ميجابايت'}
    
    try:
        safe_filename = generate_secure_filename(file.filename)
        
        os.makedirs(upload_folder, exist_ok=True)
        
        file_path = os.path.join(upload_folder, safe_filename)
        file.save(file_path)
        
        if not validate_mime_type(file_path):
            os.remove(file_path)
            return False, {'error': 'نوع الملف غير صالح. يجب أن يكون صورة PNG أو JPEG فقط'}
        
        return True, {'filename': safe_filename, 'path': file_path}
        
    except Exception as e:
        current_app.logger.error(f'خطأ في حفظ الملف: {str(e)}')
        return False, {'error': f'فشل في حفظ الملف: {str(e)}'}


class AccountLockoutService:
    """Service for managing account lockout with Redis"""
    
    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 30
    ATTEMPT_WINDOW_MINUTES = 15
    
    def __init__(self):
        redis_url = os.environ.get('REDIS_URL', '')
        if redis_url:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                self.redis_available = True
            except Exception as e:
                print(f"Redis connection failed for lockout service: {e}. Using in-memory fallback.")
                self.redis_client = None
                self.redis_available = False
                self.memory_store = {}
        else:
            self.redis_client = None
            self.redis_available = False
            self.memory_store = {}
    
    def _get_attempts_key(self, username: str, ip_address: str) -> str:
        """Generate Redis key for login attempts"""
        return f"login_attempts:{username}:{ip_address}"
    
    def _get_lockout_key(self, username: str) -> str:
        """Generate Redis key for account lockout"""
        return f"account_locked:{username}"
    
    def record_failed_attempt(self, username: str, ip_address: str) -> Tuple[bool, Optional[datetime]]:
        """
        Record a failed login attempt.
        
        Args:
            username: Username
            ip_address: IP address
            
        Returns:
            Tuple of (is_locked, locked_until_datetime)
        """
        attempts_key = self._get_attempts_key(username, ip_address)
        lockout_key = self._get_lockout_key(username)
        
        if self.redis_available and self.redis_client:
            try:
                self.redis_client.incr(attempts_key)
                
                self.redis_client.expire(attempts_key, self.ATTEMPT_WINDOW_MINUTES * 60)
                
                attempts = int(self.redis_client.get(attempts_key) or 0)
                
                if attempts >= self.MAX_FAILED_ATTEMPTS:
                    locked_until = datetime.utcnow() + timedelta(minutes=self.LOCKOUT_DURATION_MINUTES)
                    self.redis_client.setex(
                        lockout_key,
                        self.LOCKOUT_DURATION_MINUTES * 60,
                        locked_until.isoformat()
                    )
                    
                    self.redis_client.delete(attempts_key)
                    
                    return True, locked_until
                
                return False, None
                
            except Exception as e:
                print(f"Redis failed attempt recording failed: {e}")
                key = f"{username}:{ip_address}"
                if key not in self.memory_store:
                    self.memory_store[key] = {
                        'attempts': 0,
                        'first_attempt': datetime.utcnow()
                    }
                
                data = self.memory_store[key]
                
                if (datetime.utcnow() - data['first_attempt']).total_seconds() > self.ATTEMPT_WINDOW_MINUTES * 60:
                    data['attempts'] = 0
                    data['first_attempt'] = datetime.utcnow()
                
                data['attempts'] += 1
                
                if data['attempts'] >= self.MAX_FAILED_ATTEMPTS:
                    locked_until = datetime.utcnow() + timedelta(minutes=self.LOCKOUT_DURATION_MINUTES)
                    self.memory_store[f"locked:{username}"] = locked_until
                    return True, locked_until
                
                return False, None
        else:
            key = f"{username}:{ip_address}"
            if key not in self.memory_store:
                self.memory_store[key] = {
                    'attempts': 0,
                    'first_attempt': datetime.utcnow()
                }
            
            data = self.memory_store[key]
            
            if (datetime.utcnow() - data['first_attempt']).total_seconds() > self.ATTEMPT_WINDOW_MINUTES * 60:
                data['attempts'] = 0
                data['first_attempt'] = datetime.utcnow()
            
            data['attempts'] += 1
            
            if data['attempts'] >= self.MAX_FAILED_ATTEMPTS:
                locked_until = datetime.utcnow() + timedelta(minutes=self.LOCKOUT_DURATION_MINUTES)
                self.memory_store[f"locked:{username}"] = locked_until
                return True, locked_until
            
            return False, None
    
    def is_account_locked(self, username: str) -> Tuple[bool, Optional[datetime]]:
        """
        Check if an account is locked.
        
        Args:
            username: Username
            
        Returns:
            Tuple of (is_locked, locked_until_datetime)
        """
        lockout_key = self._get_lockout_key(username)
        
        if self.redis_available and self.redis_client:
            try:
                locked_until_str = self.redis_client.get(lockout_key)
                if locked_until_str:
                    locked_until = datetime.fromisoformat(locked_until_str)
                    if locked_until > datetime.utcnow():
                        return True, locked_until
                    else:
                        self.redis_client.delete(lockout_key)
                        return False, None
                return False, None
                
            except Exception as e:
                print(f"Redis lockout check failed: {e}")
                locked_until = self.memory_store.get(f"locked:{username}")
                if locked_until and locked_until > datetime.utcnow():
                    return True, locked_until
                elif locked_until:
                    del self.memory_store[f"locked:{username}"]
                return False, None
        else:
            locked_until = self.memory_store.get(f"locked:{username}")
            if locked_until and locked_until > datetime.utcnow():
                return True, locked_until
            elif locked_until:
                del self.memory_store[f"locked:{username}"]
            return False, None
    
    def clear_failed_attempts(self, username: str, ip_address: str) -> None:
        """
        Clear failed login attempts (called on successful login).
        
        Args:
            username: Username
            ip_address: IP address
        """
        attempts_key = self._get_attempts_key(username, ip_address)
        
        if self.redis_available and self.redis_client:
            try:
                self.redis_client.delete(attempts_key)
            except Exception as e:
                print(f"Redis clear attempts failed: {e}")
                key = f"{username}:{ip_address}"
                if key in self.memory_store:
                    del self.memory_store[key]
        else:
            key = f"{username}:{ip_address}"
            if key in self.memory_store:
                del self.memory_store[key]
    
    def unlock_account(self, username: str) -> bool:
        """
        Manually unlock an account (admin action).
        
        Args:
            username: Username
            
        Returns:
            True if account was unlocked, False otherwise
        """
        lockout_key = self._get_lockout_key(username)
        
        if self.redis_available and self.redis_client:
            try:
                result = self.redis_client.delete(lockout_key)
                return result > 0
            except Exception as e:
                print(f"Redis unlock account failed: {e}")
                key = f"locked:{username}"
                if key in self.memory_store:
                    del self.memory_store[key]
                    return True
                return False
        else:
            key = f"locked:{username}"
            if key in self.memory_store:
                del self.memory_store[key]
                return True
            return False
    
    def get_remaining_attempts(self, username: str, ip_address: str) -> int:
        """
        Get remaining login attempts before lockout.
        
        Args:
            username: Username
            ip_address: IP address
            
        Returns:
            Number of remaining attempts
        """
        attempts_key = self._get_attempts_key(username, ip_address)
        
        if self.redis_available and self.redis_client:
            try:
                attempts = int(self.redis_client.get(attempts_key) or 0)
                return max(0, self.MAX_FAILED_ATTEMPTS - attempts)
            except Exception as e:
                print(f"Redis get remaining attempts failed: {e}")
                key = f"{username}:{ip_address}"
                data = self.memory_store.get(key, {})
                attempts = data.get('attempts', 0)
                return max(0, self.MAX_FAILED_ATTEMPTS - attempts)
        else:
            key = f"{username}:{ip_address}"
            data = self.memory_store.get(key, {})
            attempts = data.get('attempts', 0)
            return max(0, self.MAX_FAILED_ATTEMPTS - attempts)


lockout_service = AccountLockoutService()
