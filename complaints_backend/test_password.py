#!/usr/bin/env python3
"""Test password verification"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from werkzeug.security import generate_password_hash, check_password_hash
from src.database.db import db
from src.models.complaint import User
from src.main import app

def test_password():
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            print("Admin not found!")
            return
        
        print(f"Username: {admin.username}")
        print(f"Email: {admin.email}")
        print(f"Password hash length: {len(admin.password_hash)}")
        print(f"Hash starts with: {admin.password_hash[:20]}...")
        
        # Test the password
        test_password = "Admin@123456"
        result = check_password_hash(admin.password_hash, test_password)
        print(f"\nPassword verification result: {result}")
        
        # Generate a new hash to compare
        new_hash = generate_password_hash(test_password)
        print(f"New hash example: {new_hash[:50]}...")
        
        # Try verifying the new hash
        print(f"New hash verifies: {check_password_hash(new_hash, test_password)}")

if __name__ == '__main__':
    test_password()
