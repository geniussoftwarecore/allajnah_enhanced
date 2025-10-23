from marshmallow import Schema, fields

class SubscriptionCreateSchema(Schema):
    """Schema for creating a subscription"""
    user_id = fields.Str(required=True)
    plan = fields.Str(missing='annual')
    grace_period_enabled = fields.Bool(missing=True)
