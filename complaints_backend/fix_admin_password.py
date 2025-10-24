#!/usr/bin/env python3
"""Fix admin password"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from src.database.db import db
from src.models.complaint import User
from src.main import app

def fix_password():
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            print("ERROR: Admin not found!")
            return False
        
        # New password
        new_password = "Admin@123456"
        
        # Generate hash
        new_hash = generate_password_hash(new_password)
        
        # Test the new hash immediately
        test_result = check_password_hash(new_hash, new_password)
        print(f"New hash verification test: {test_result}")
        
        if not test_result:
            print("ERROR: Hash verification failed!")
            return False
        
        # Update the admin password
        admin.password_hash = new_hash
        admin.last_password_change = datetime.utcnow()
        db.session.commit()
        
        # Verify it was saved correctly
        admin_check = User.query.filter_by(username='admin').first()
        verify_result = check_password_hash(admin_check.password_hash, new_password)
        
        print("\n" + "="*60)
        print("✅ Admin password updated successfully!")
        print("="*60)
        print(f"Username: admin")
        print(f"Password: {new_password}")
        print(f"Verification: {'PASSED' if verify_result else 'FAILED'}")
        print("="*60)
        
        return verify_result

if __name__ == '__main__':
    success = fix_password()
    sys.exit(0 if success else 1)
