from marshmallow import Schema, fields, validate, validates, ValidationError

class InitialSetupSchema(Schema):
    """Schema for initial system setup - creating first admin"""
    username = fields.Str(
        required=True,
        validate=[
            validate.Length(min=3, max=50, error='اسم المستخدم يجب أن يكون بين 3 و 50 حرفاً'),
            validate.Regexp(
                r'^[a-zA-Z0-9_-]+$',
                error='اسم المستخدم يجب أن يحتوي على أحرف إنجليزية وأرقام و _ و - فقط'
            )
        ]
    )
    email = fields.Email(required=True, error_messages={'invalid': 'البريد الإلكتروني غير صالح'})
    password = fields.Str(
        required=True,
        validate=validate.Length(min=8, error='كلمة المرور يجب أن تكون 8 أحرف على الأقل')
    )
    full_name = fields.Str(
        required=True,
        validate=validate.Length(min=2, max=255, error='الاسم الكامل يجب أن يكون بين 2 و 255 حرفاً')
    )
    phone_number = fields.Str(
        allow_none=True,
        validate=validate.Length(max=50, error='رقم الهاتف طويل جداً')
    )
    address = fields.Str(allow_none=True)
    
    @validates('phone_number')
    def validate_phone(self, value):
        if value:
            cleaned = value.replace('+', '').replace('-', '').replace(' ', '')
            if not cleaned.isdigit():
                raise ValidationError('رقم الهاتف يجب أن يحتوي على أرقام فقط')
            if value.startswith('+967'):
                if len(cleaned) < 12:
                    raise ValidationError('رقم الهاتف اليمني غير صالح')

class UserCreateSchema(Schema):
    """Schema for creating a new user"""
    username = fields.Str(
        required=True,
        validate=[
            validate.Length(min=3, max=50, error='اسم المستخدم يجب أن يكون بين 3 و 50 حرفاً'),
            validate.Regexp(
                r'^[a-zA-Z0-9_-]+$',
                error='اسم المستخدم يجب أن يحتوي على أحرف وأرقام و _ و - فقط'
            )
        ]
    )
    email = fields.Email(required=True, error_messages={'invalid': 'البريد الإلكتروني غير صالح'})
    password = fields.Str(
        required=True,
        validate=validate.Length(min=8, error='كلمة المرور يجب أن تكون 8 أحرف على الأقل')
    )
    full_name = fields.Str(
        required=True,
        validate=validate.Length(min=2, max=255, error='الاسم الكامل يجب أن يكون بين 2 و 255 حرفاً')
    )
    phone_number = fields.Str(
        allow_none=True,
        validate=validate.Length(max=50, error='رقم الهاتف طويل جداً')
    )
    address = fields.Str(allow_none=True)
    role_id = fields.Int(required=True)
    
    @validates('phone_number')
    def validate_phone(self, value):
        if value:
            cleaned = value.replace('+', '').replace('-', '').replace(' ', '')
            if not cleaned.isdigit():
                raise ValidationError('رقم الهاتف يجب أن يحتوي على أرقام فقط')
            if value.startswith('+967'):
                if len(cleaned) < 12:
                    raise ValidationError('رقم الهاتف اليمني غير صالح')

class UserUpdateSchema(Schema):
    """Schema for updating user profile"""
    email = fields.Email(error_messages={'invalid': 'البريد الإلكتروني غير صالح'})
    full_name = fields.Str(
        validate=validate.Length(min=2, max=255, error='الاسم الكامل يجب أن يكون بين 2 و 255 حرفاً')
    )
    phone_number = fields.Str(validate=validate.Length(max=50, error='رقم الهاتف طويل جداً'))
    address = fields.Str()
    
    @validates('phone_number')
    def validate_phone(self, value):
        if value:
            cleaned = value.replace('+', '').replace('-', '').replace(' ', '')
            if not cleaned.isdigit():
                raise ValidationError('رقم الهاتف يجب أن يحتوي على أرقام فقط')

class UserLoginSchema(Schema):
    """Schema for user login"""
    username = fields.Str(required=True, error_messages={'required': 'اسم المستخدم مطلوب'})
    password = fields.Str(required=True, error_messages={'required': 'كلمة المرور مطلوبة'})
    otp_code = fields.Str(allow_none=True)

class ChangePasswordSchema(Schema):
    """Schema for changing password"""
    current_password = fields.Str(
        required=True,
        error_messages={'required': 'كلمة المرور الحالية مطلوبة'}
    )
    new_password = fields.Str(
        required=True,
        validate=validate.Length(min=8, error='كلمة المرور الجديدة يجب أن تكون 8 أحرف على الأقل'),
        error_messages={'required': 'كلمة المرور الجديدة مطلوبة'}
    )

class RefreshTokenSchema(Schema):
    """Schema for refresh token request"""
    refresh_token = fields.Str(
        required=True,
        error_messages={'required': 'رمز التحديث مطلوب'}
    )

class RevokeSessionSchema(Schema):
    """Schema for revoking a session"""
    refresh_token = fields.Str(
        required=True,
        error_messages={'required': 'رمز الجلسة مطلوب'}
    )
