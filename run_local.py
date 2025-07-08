#!/usr/bin/env python3
"""
Local development server
"""

import os
from app import create_app

if __name__ == '__main__':
    # Set development environment
    os.environ['FLASK_CONFIG'] = 'development'
    os.environ['FLASK_ENV'] = 'development'
    
    # Create app
    app = create_app('development')
    
    print("🚀 Starting Archive Backup System locally...")
    print("📍 Web interface: http://localhost:8000")
    print("📍 API docs: http://localhost:8000/health")
    print("🛑 Press Ctrl+C to stop")
    
    # Run development server
    app.run(
        host='0.0.0.0',
        port=8000,
        debug=True,
        use_reloader=True
    )