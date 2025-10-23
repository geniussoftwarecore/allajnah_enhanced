from marshmallow import Schema, fields, validate, validates, ValidationError

class PaymentCreateSchema(Schema):
    """Schema for creating a payment"""
    method_id = fields.Int(required=True)
    sender_name = fields.Str(
        required=True,
        validate=validate.Length(min=2, max=255, error='اسم المُرسل يجب أن يكون بين 2 و 255 حرفاً')
    )
    sender_phone = fields.Str(
        required=True,
        validate=validate.Length(min=5, max=50, error='رقم هاتف المُرسل يجب أن يكون بين 5 و 50 حرفاً')
    )
    transaction_reference = fields.Str(
        required=True,
        validate=validate.Length(min=3, max=255, error='مرجع العملية يجب أن يكون بين 3 و 255 حرفاً')
    )
    amount = fields.Float(
        required=True,
        validate=validate.Range(min=0.01, error='المبلغ يجب أن يكون أكبر من صفر')
    )
    currency = fields.Str(
        missing='YER',
        validate=validate.Length(max=3, error='رمز العملة يجب أن يكون 3 أحرف كحد أقصى')
    )
    payment_date = fields.Date(required=True)
    
    @validates('sender_phone')
    def validate_sender_phone(self, value):
        if value:
            cleaned = value.replace('+', '').replace('-', '').replace(' ', '')
            if not cleaned.isdigit():
                raise ValidationError('رقم الهاتف يجب أن يحتوي على أرقام فقط')
            if value.startswith('+967'):
                if len(cleaned) < 12:
                    raise ValidationError('رقم الهاتف اليمني غير صالح')

class PaymentMethodCreateSchema(Schema):
    """Schema for creating a payment method"""
    name = fields.Str(
        required=True,
        validate=validate.Length(min=2, max=255, error='اسم طريقة الدفع يجب أن يكون بين 2 و 255 حرفاً')
    )
    account_number = fields.Str(
        required=True,
        validate=validate.Length(min=3, max=255, error='رقم الحساب يجب أن يكون بين 3 و 255 حرفاً')
    )
    account_holder = fields.Str(
        required=True,
        validate=validate.Length(min=2, max=255, error='اسم صاحب الحساب يجب أن يكون بين 2 و 255 حرفاً')
    )
    notes = fields.Str(allow_none=True)
    is_active = fields.Bool(missing=True)
    display_order = fields.Int(allow_none=True)

class PaymentMethodUpdateSchema(Schema):
    """Schema for updating a payment method"""
    name = fields.Str(validate=validate.Length(min=2, max=255, error='اسم طريقة الدفع يجب أن يكون بين 2 و 255 حرفاً'))
    account_number = fields.Str(validate=validate.Length(min=3, max=255, error='رقم الحساب يجب أن يكون بين 3 و 255 حرفاً'))
    account_holder = fields.Str(validate=validate.Length(min=2, max=255, error='اسم صاحب الحساب يجب أن يكون بين 2 و 255 حرفاً'))
    notes = fields.Str()
    is_active = fields.Bool()
    display_order = fields.Int()
