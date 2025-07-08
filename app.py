#!/usr/bin/env python3
"""
Archive Backup - Flask App Entry Point
Python/Flask implementation of Archive.org backup system
"""

import os
from app import create_app
from app.models.show_metadata import db
from flask_migrate import upgrade

# Create app instance
app = create_app(os.getenv('FLASK_CONFIG') or 'default')

@app.shell_context_processor
def make_shell_context():
    """Make database models available in flask shell"""
    from app.models.show_metadata import ShowMetadata, ShowFile, ShowMP3, BackupJob
    return dict(db=db, ShowMetadata=ShowMetadata, ShowFile=ShowFile, ShowMP3=ShowMP3, BackupJob=BackupJob)

@app.cli.command()
def deploy():
    """Deploy the application"""
    # Create database tables
    db.create_all()
    
    # Create storage directories
    os.makedirs(app.config['METADATA_STORAGE_PATH'], exist_ok=True)
    os.makedirs(app.config['FILES_STORAGE_PATH'], exist_ok=True)
    
    print("Database tables created successfully!")
    print(f"Storage directories created at: {app.config['STORAGE_PATH']}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 