import re
from typing import Tuple, List

COMMON_PASSWORDS = {
    'password', '12345678', '123456789', '1234567890', 'qwerty123', 'password123',
    'admin123', 'letmein', 'welcome', 'monkey', '1234567', '12345', '123456',
    'password1', 'abc123', 'qwerty', 'admin', 'letmein1', 'welcome1', 'password!',
    'Aa123456', 'P@ssw0rd', 'P@ssword', 'Pass123', 'Pass1234', 'Password123!',
    '11111111', '00000000', 'football', 'baseball', 'dragon', 'master', 'sunshine',
    'iloveyou', 'princess', 'superman', 'trustno1', 'hello123', 'welcome123',
    '1q2w3e4r', 'zxcvbnm', 'asdfghjk', 'qwertyuiop', '1qaz2wsx', 'password@123',
    'admin@123', 'root', 'toor', 'pass', 'test', 'guest', 'oracle', 'postgres',
    'mysql', 'user', 'usuario', 'senha', 'senha123', 'senha@123', 'qwerty12345',
    '123qwe', 'qwe123', 'qweasd', 'asdzxc', 'zxcasd', '1234qwer', 'qwer1234',
    'access', 'access123', 'administrator', 'Administrator', 'changeme', 'password12',
    'temp123', 'temp1234', 'temporary', 'welcome@123', 'monkey123', 'dragon123',
    'master123', 'superman123', 'batman', 'batman123', 'spider', 'spider123',
    '111111', '222222', '333333', '444444', '555555', '666666', '777777', '888888',
    '999999', '000000', '123321', '654321', '1234321', '12344321', '123454321',
    'abc123456', 'abcd1234', '1234abcd', 'password!123', 'admin!123', 'P@ssw0rd123'
}

def validate_password_strength(password: str) -> Tuple[bool, List[str]]:
    """
    Validate password strength according to security policy.
    
    Args:
        password: The password to validate
        
    Returns:
        Tuple of (is_valid, error_messages_in_arabic)
    """
    errors = []
    
    if not password:
        return False, ['كلمة المرور مطلوبة']
    
    if len(password) < 8:
        errors.append('كلمة المرور يجب أن تكون 8 أحرف على الأقل')
    
    if len(password) > 128:
        errors.append('كلمة المرور طويلة جداً (الحد الأقصى 128 حرف)')
    
    if not re.search(r'[A-Z]', password):
        errors.append('كلمة المرور يجب أن تحتوي على حرف كبير واحد على الأقل (A-Z)')
    
    if not re.search(r'[a-z]', password):
        errors.append('كلمة المرور يجب أن تحتوي على حرف صغير واحد على الأقل (a-z)')
    
    if not re.search(r'[0-9]', password):
        errors.append('كلمة المرور يجب أن تحتوي على رقم واحد على الأقل (0-9)')
    
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>?/\\|`~]', password):
        errors.append('كلمة المرور يجب أن تحتوي على رمز خاص واحد على الأقل (!@#$%^&* إلخ)')
    
    if password.lower() in COMMON_PASSWORDS:
        errors.append('كلمة المرور شائعة جداً. يرجى اختيار كلمة مرور أقوى')
    
    password_lower = password.lower()
    for common_pwd in COMMON_PASSWORDS:
        if common_pwd in password_lower and len(common_pwd) > 5:
            errors.append('كلمة المرور تحتوي على أنماط شائعة. يرجى اختيار كلمة مرور أقوى')
            break
    
    if re.search(r'(.)\1{2,}', password):
        errors.append('كلمة المرور تحتوي على أحرف متكررة كثيرة')
    
    sequential_patterns = [
        '123', '234', '345', '456', '567', '678', '789',
        'abc', 'bcd', 'cde', 'def', 'efg', 'fgh',
        'qwe', 'wer', 'ert', 'rty', 'tyu', 'yui', 'uio', 'iop',
        'asd', 'sdf', 'dfg', 'fgh', 'ghj', 'hjk', 'jkl',
        'zxc', 'xcv', 'cvb', 'vbn', 'bnm'
    ]
    
    password_lower = password.lower()
    for pattern in sequential_patterns:
        if pattern in password_lower:
            errors.append('كلمة المرور تحتوي على تسلسلات سهلة التخمين')
            break
    
    is_valid = len(errors) == 0
    return is_valid, errors

def get_password_strength_score(password: str) -> int:
    """
    Calculate password strength score (0-100).
    
    Args:
        password: The password to evaluate
        
    Returns:
        Integer score from 0 to 100
    """
    if not password:
        return 0
    
    score = 0
    
    score += min(len(password) * 2, 30)
    
    if re.search(r'[A-Z]', password):
        score += 10
    if re.search(r'[a-z]', password):
        score += 10
    if re.search(r'[0-9]', password):
        score += 10
    if re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>?/\\|`~]', password):
        score += 15
    
    uppercase_count = len(re.findall(r'[A-Z]', password))
    lowercase_count = len(re.findall(r'[a-z]', password))
    digit_count = len(re.findall(r'[0-9]', password))
    special_count = len(re.findall(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>?/\\|`~]', password))
    
    if uppercase_count > 1:
        score += 5
    if lowercase_count > 1:
        score += 5
    if digit_count > 1:
        score += 5
    if special_count > 1:
        score += 5
    
    if password.lower() in COMMON_PASSWORDS:
        score = max(0, score - 40)
    
    if re.search(r'(.)\1{2,}', password):
        score = max(0, score - 15)
    
    return min(score, 100)

def get_strength_label(score: int) -> str:
    """
    Get Arabic label for password strength score.
    
    Args:
        score: Password strength score (0-100)
        
    Returns:
        Arabic strength label
    """
    if score < 30:
        return 'ضعيفة جداً'
    elif score < 50:
        return 'ضعيفة'
    elif score < 70:
        return 'متوسطة'
    elif score < 90:
        return 'قوية'
    else:
        return 'قوية جداً'
