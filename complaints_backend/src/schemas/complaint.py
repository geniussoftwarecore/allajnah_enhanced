from marshmallow import Schema, fields, validate, validates, ValidationError

class ComplaintCreateSchema(Schema):
    """Schema for creating a new complaint"""
    title = fields.Str(
        required=True,
        validate=validate.Length(min=5, max=255, error='العنوان يجب أن يكون بين 5 و 255 حرفاً')
    )
    description = fields.Str(
        required=True,
        validate=validate.Length(min=10, error='الوصف يجب أن يكون 10 أحرف على الأقل')
    )
    category_id = fields.Int(required=True)
    priority = fields.Str(
        missing='Medium',
        validate=validate.OneOf(
            ['Low', 'Medium', 'High', 'Urgent'],
            error='الأولوية يجب أن تكون واحدة من: Low, Medium, High, Urgent'
        )
    )

class ComplaintUpdateSchema(Schema):
    """Schema for updating a complaint"""
    title = fields.Str(validate=validate.Length(min=5, max=255, error='العنوان يجب أن يكون بين 5 و 255 حرفاً'))
    description = fields.Str(validate=validate.Length(min=10, error='الوصف يجب أن يكون 10 أحرف على الأقل'))
    category_id = fields.Int()
    priority = fields.Str(
        validate=validate.OneOf(
            ['Low', 'Medium', 'High', 'Urgent'],
            error='الأولوية يجب أن تكون واحدة من: Low, Medium, High, Urgent'
        )
    )
    status_id = fields.Int()
    resolution_details = fields.Str()

class CommentCreateSchema(Schema):
    """Schema for creating a comment"""
    comment_text = fields.Str(
        required=True,
        validate=validate.Length(min=1, error='التعليق لا يمكن أن يكون فارغاً')
    )
