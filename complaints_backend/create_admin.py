#!/usr/bin/env python3
"""
Create default admin account
"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from werkzeug.security import generate_password_hash
from datetime import datetime
from src.database.db import db
from src.models.complaint import User, Role
from src.main import app

def create_admin():
    """Create default admin account"""
    with app.app_context():
        # Check if admin already exists
        admin_role = Role.query.filter_by(role_name='Higher Committee').first()
        if not admin_role:
            print("Error: Higher Committee role not found. Please run init_data.py first.")
            return False
        
        existing_admin = User.query.filter_by(role_id=admin_role.role_id).first()
        if existing_admin:
            print(f"Admin account already exists: {existing_admin.username}")
            return True
        
        # Create admin user
        admin_username = "admin"
        admin_password = "Admin@123456"
        admin_email = "admin@complaints.local"
        admin_full_name = "مسؤول النظام"
        
        hashed_password = generate_password_hash(admin_password)
        
        admin_user = User(
            username=admin_username,
            email=admin_email,
            password_hash=hashed_password,
            full_name=admin_full_name,
            phone_number="",
            address="",
            role_id=admin_role.role_id,
            is_active=True,
            last_password_change=datetime.utcnow()
        )
        
        db.session.add(admin_user)
        db.session.commit()
        
        print("\n✅ Admin account created successfully!")
        print("\n" + "="*60)
        print("LOGIN CREDENTIALS:")
        print("="*60)
        print(f"Username: {admin_username}")
        print(f"Password: {admin_password}")
        print("="*60)
        print("\n⚠️  IMPORTANT: Please change this password after first login!")
        
        return True

if __name__ == '__main__':
    success = create_admin()
    if not success:
        sys.exit(1)
