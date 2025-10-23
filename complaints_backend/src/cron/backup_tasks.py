#!/usr/bin/env python3
"""
Automated Backup Tasks
Runs daily database backups and cleanup

Usage:
    python complaints_backend/src/cron/backup_tasks.py

Cron Setup (Linux/Mac):
    0 2 * * * cd /path/to/project && python complaints_backend/src/cron/backup_tasks.py

Task Scheduler (Windows):
    Use Task Scheduler to run this script daily at 2 AM
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from flask import Flask
from src.database.db import db
from src.services.backup_service import BackupService

def setup_app():
    """Setup Flask app for standalone execution"""
    app = Flask(__name__)
    
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            "pool_recycle": 300,
            "pool_pre_ping": True,
        }
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), '..', 'database', 'app.db')}"
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    
    return app

def run_backup_job():
    """Execute backup and cleanup tasks"""
    app = setup_app()
    
    with app.app_context():
        print("=" * 60)
        print("Starting Automated Backup Process")
        print(f"Timestamp: {os.popen('date').read().strip()}")
        print("=" * 60)
        
        backup_service = BackupService()
        
        print("\n[1/3] Creating database backup...")
        backup_result = backup_service.create_backup()
        
        if backup_result['success']:
            print(f"✓ Backup created successfully")
            print(f"  - Filename: {backup_result['filename']}")
            print(f"  - Size: {backup_result['size_bytes'] / (1024 * 1024):.2f} MB")
            print(f"  - Checksum: {backup_result['checksum'][:16]}...")
        else:
            print(f"✗ Backup failed: {backup_result['error']}")
            return 1
        
        print("\n[2/3] Cleaning up old backups...")
        cleanup_result = backup_service.cleanup_old_backups()
        
        if cleanup_result['success']:
            print(f"✓ Cleanup completed")
            print(f"  - Deleted: {cleanup_result['deleted_count']} old backups")
            print(f"  - Retained: {cleanup_result['kept_count']} backups")
        else:
            print(f"⚠ Cleanup had issues: {cleanup_result.get('error', 'Unknown error')}")
        
        print("\n[3/3] Listing current backups...")
        backups = backup_service.list_backups()
        print(f"✓ Total backups: {len(backups)}")
        
        if backups:
            print("\nRecent backups:")
            for backup in backups[:5]:
                print(f"  - {backup['filename']}: {backup['size_mb']:.2f} MB ({backup['status']})")
        
        print("\n" + "=" * 60)
        print("Backup process completed successfully")
        print("=" * 60)
        
        return 0

def main():
    """Main entry point"""
    try:
        exit_code = run_backup_job()
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n✗ FATAL ERROR: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
