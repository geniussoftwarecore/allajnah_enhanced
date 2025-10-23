#!/usr/bin/env python3
"""
Settings and Payment Methods initialization script
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.models.complaint import db, Settings, PaymentMethod
from flask import Flask

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SESSION_SECRET', 'dev-secret-key')
    database_url = os.environ.get('DATABASE_URL', 
                                  f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}")
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app

def init_settings():
    """Initialize default system settings"""
    settings_data = [
        {
            'key': 'subscription_price_annual',
            'value': '50000',
            'description': 'سعر الاشتراك السنوي بالريال اليمني'
        },
        {
            'key': 'currency',
            'value': 'YER',
            'description': 'العملة المستخدمة (YER, USD, SAR)'
        },
        {
            'key': 'grace_period_days',
            'value': '7',
            'description': 'عدد أيام السماح بعد انتهاء الاشتراك'
        },
        {
            'key': 'enable_grace_period',
            'value': 'true',
            'description': 'تفعيل فترة السماح'
        },
    ]
    
    for setting_data in settings_data:
        existing = Settings.query.filter_by(key=setting_data['key']).first()
        if not existing:
            setting = Settings(**setting_data)
            db.session.add(setting)
            print(f"Added setting: {setting_data['key']} = {setting_data['value']}")
        else:
            print(f"Setting already exists: {setting_data['key']}")

def init_payment_methods():
    """Initialize default payment methods"""
    payment_methods_data = [
        {
            'name': 'يمن موبايل',
            'account_number': '771234567',
            'account_holder': 'نظام الشكاوى الإلكتروني',
            'is_active': True,
            'display_order': 1
        },
        {
            'name': 'MTN',
            'account_number': '781234567',
            'account_holder': 'نظام الشكاوى الإلكتروني',
            'is_active': True,
            'display_order': 2
        },
    ]
    
    for method_data in payment_methods_data:
        existing = PaymentMethod.query.filter_by(name=method_data['name']).first()
        if not existing:
            method = PaymentMethod(**method_data)
            db.session.add(method)
            print(f"Added payment method: {method_data['name']}")
        else:
            print(f"Payment method already exists: {method_data['name']}")

def main():
    """Main initialization function"""
    app = create_app()
    
    with app.app_context():
        print("Initializing settings...")
        init_settings()
        
        print("\nInitializing payment methods...")
        init_payment_methods()
        
        try:
            db.session.commit()
            print("\n✅ Settings and payment methods initialized successfully!")
            return True
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error: {str(e)}")
            return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
