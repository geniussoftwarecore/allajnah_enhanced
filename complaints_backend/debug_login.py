#!/usr/bin/env python3
"""Debug login issue"""
from werkzeug.security import check_password_hash
import psycopg2
import os

# Get database connection from environment
db_url = os.environ.get('DATABASE_URL')
if not db_url:
    print("ERROR: DATABASE_URL not set")
    exit(1)

# Connect to database
conn = psycopg2.connect(db_url)
cur = conn.cursor()

# Get admin user
cur.execute("SELECT username, password_hash, is_active FROM users WHERE username = 'admin'")
row = cur.fetchone()

if not row:
    print("ERROR: Admin user not found")
    exit(1)

username, password_hash, is_active = row

print("="*60)
print("ADMIN USER DEBUG INFO")
print("="*60)
print(f"Username: {username}")
print(f"Is Active: {is_active}")
print(f"Password Hash Length: {len(password_hash)}")
print(f"Hash Prefix: {password_hash[:50]}")
print()

# Test password verification
test_password = "Admin@123456"
result = check_password_hash(password_hash, test_password)

print(f"Password to test: {test_password}")
print(f"Verification Result: {result}")
print("="*60)

if result:
    print("✅ PASSWORD VERIFICATION SUCCESSFUL!")
else:
    print("❌ PASSWORD VERIFICATION FAILED!")
    print("\nTrying to generate new hash...")
    from werkzeug.security import generate_password_hash
    new_hash = generate_password_hash(test_password)
    print(f"New hash: {new_hash[:50]}...")
    print(f"New hash verifies: {check_password_hash(new_hash, test_password)}")

cur.close()
conn.close()
