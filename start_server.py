#!/usr/bin/env python3

import os
import sys
from app import create_app

if __name__ == '__main__':
    # Set environment
    os.environ['FLASK_CONFIG'] = 'development'
    os.environ['FLASK_ENV'] = 'development'
    
    # Create app
    app = create_app('development')
    
    # Get port from command line or default to 3000
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    
    print(f"🚀 Archive Backup System")
    print(f"📍 Web Interface: http://localhost:{port}")
    print(f"📍 Health Check: http://localhost:{port}/health")
    print(f"📍 API Base: http://localhost:{port}/api")
    print("🛑 Press Ctrl+C to stop")
    print("-" * 50)
    
    try:
        app.run(
            host='0.0.0.0',
            port=port,
            debug=True,
            use_reloader=False,  # Disable reloader to avoid issues
            threaded=True
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)