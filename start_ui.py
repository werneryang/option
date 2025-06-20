#!/usr/bin/env python3
"""
Simple UI Launcher with Port Detection
"""

import subprocess
import sys
import socket
from pathlib import Path

def check_port(port):
    """Check if a port is available"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) != 0

def find_available_port(start_port=8501, max_attempts=10):
    """Find an available port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        if check_port(port):
            return port
    return None

def main():
    # Find available port
    port = find_available_port()
    if not port:
        print("❌ No available ports found in range 8501-8510")
        sys.exit(1)
    
    # Get app path
    app_path = Path(__file__).parent / "src" / "ui" / "app.py"
    
    if not app_path.exists():
        print(f"❌ App not found: {app_path}")
        sys.exit(1)
    
    print(f"🚀 Starting Options Analysis Platform on port {port}")
    print(f"🌐 Open in browser: http://localhost:{port}")
    print("⏹️  Press Ctrl+C to stop")
    print("=" * 50)
    
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", str(app_path),
            "--server.port", str(port),
            "--server.address", "localhost",
            "--browser.gatherUsageStats", "false",
            "--server.headless", "true"
        ])
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()