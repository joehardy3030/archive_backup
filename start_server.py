#!/usr/bin/env python3

import os
import sys
import signal
import subprocess
import socket
import time
from app import create_app

def is_port_in_use(port):
    """Check if a port is currently in use"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            result = sock.connect_ex(('localhost', port))
            return result == 0
    except:
        return False

def kill_process_on_port(port):
    """Kill any process using the specified port"""
    killed = False
    
    # Try different methods depending on the OS
    if os.name == 'nt':  # Windows
        try:
            # Use netstat to find process using the port
            result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if f':{port}' in line and 'LISTENING' in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        pid = parts[-1]
                        try:
                            subprocess.run(['taskkill', '/F', '/PID', pid], check=True)
                            print(f"🔥 Killed existing process (PID: {pid}) on port {port}")
                            killed = True
                        except subprocess.CalledProcessError:
                            pass
        except Exception as e:
            print(f"⚠️  Could not kill Windows process: {e}")
    
    else:  # Unix-like systems (macOS, Linux)
        try:
            # Method 1: Use lsof to find process using the port
            result = subprocess.run(['lsof', '-ti', f':{port}'], 
                                  capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid:
                        try:
                            os.kill(int(pid), signal.SIGTERM)
                            print(f"🔥 Killed existing process (PID: {pid}) on port {port}")
                            killed = True
                            time.sleep(0.5)  # Give it time to terminate
                            
                            # If it's still running, force kill
                            try:
                                os.kill(int(pid), signal.SIGKILL)
                                print(f"🔥 Force killed stubborn process (PID: {pid})")
                            except ProcessLookupError:
                                pass  # Process already dead
                        except (ProcessLookupError, ValueError):
                            pass  # Process doesn't exist or invalid PID
        except FileNotFoundError:
            # lsof not available, try alternative method
            try:
                # Method 2: Use ss command (more modern alternative to netstat)
                result = subprocess.run(['ss', '-tulpn'], capture_output=True, text=True)
                for line in result.stdout.split('\n'):
                    if f':{port}' in line and 'LISTEN' in line:
                        # Extract PID from ss output
                        if 'pid=' in line:
                            pid_part = line.split('pid=')[1].split(',')[0]
                            try:
                                pid = int(pid_part)
                                os.kill(pid, signal.SIGTERM)
                                print(f"🔥 Killed existing process (PID: {pid}) on port {port}")
                                killed = True
                                time.sleep(0.5)
                            except (ValueError, ProcessLookupError):
                                pass
            except FileNotFoundError:
                # ss not available either, try netstat as last resort
                try:
                    result = subprocess.run(['netstat', '-tulpn'], capture_output=True, text=True)
                    for line in result.stdout.split('\n'):
                        if f':{port}' in line and 'LISTEN' in line:
                            parts = line.split()
                            if len(parts) >= 7:
                                pid_part = parts[-1]
                                if '/' in pid_part:
                                    pid = pid_part.split('/')[0]
                                    try:
                                        os.kill(int(pid), signal.SIGTERM)
                                        print(f"🔥 Killed existing process (PID: {pid}) on port {port}")
                                        killed = True
                                        time.sleep(0.5)
                                    except (ValueError, ProcessLookupError):
                                        pass
                except Exception:
                    pass
    
    return killed

def kill_flask_processes():
    """Kill any running Flask processes for this application"""
    if os.name != 'nt':  # Unix-like systems
        try:
            # Kill any process containing 'start_server.py' or 'archive_backup'
            subprocess.run(['pkill', '-f', 'start_server.py'], stderr=subprocess.DEVNULL)
            subprocess.run(['pkill', '-f', 'archive_backup'], stderr=subprocess.DEVNULL)
            print("🔥 Killed any existing Flask processes")
        except Exception:
            pass

def cleanup_and_start(port):
    """Clean up existing processes and start the server"""
    print("🧹 Checking for existing processes...")
    
    # First, kill any Flask processes by name
    kill_flask_processes()
    
    # Then, kill any process using the target port
    if is_port_in_use(port):
        print(f"⚠️  Port {port} is in use, attempting to free it...")
        killed = kill_process_on_port(port)
        
        # Wait a moment and check again
        time.sleep(1)
        if is_port_in_use(port):
            print(f"❌ Port {port} is still in use after cleanup attempt")
            print(f"💡 You may need to manually kill the process or use a different port")
            return False
        elif killed:
            print(f"✅ Port {port} is now free")
    else:
        print(f"✅ Port {port} is available")
    
    return True

if __name__ == '__main__':
    # Set environment
    os.environ['FLASK_CONFIG'] = 'development'
    os.environ['FLASK_ENV'] = 'development'
    
    # Get port from command line or default to 3000
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    
    # Clean up existing processes
    if not cleanup_and_start(port):
        print("❌ Failed to start server due to port conflict")
        sys.exit(1)
    
    # Create app
    app = create_app('development')
    
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