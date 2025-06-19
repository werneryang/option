#!/usr/bin/env python3
"""
Launch Simplified Options Analysis Platform

Quick launcher for the streamlined, single-page interface
designed for personal use.
"""

import subprocess
import sys
from pathlib import Path

def main():
    """Launch the simplified Streamlit application"""
    
    # Get the project root directory
    project_root = Path(__file__).parent
    
    # Path to the simplified Streamlit app
    app_path = project_root / "src" / "ui" / "simple_app.py"
    
    if not app_path.exists():
        print("❌ Error: Simplified app not found at", app_path)
        sys.exit(1)
    
    print("🚀 Starting Simplified Options Analysis Platform...")
    print("📊 Single-page interface for quick analysis")
    print("🎯 Features: Greeks Calculator, Strategy Builder, Volatility Analysis")
    print()
    print("🌐 Opening at: http://localhost:8502")
    print("⏹️  Press Ctrl+C to stop")
    print("=" * 50)
    
    try:
        # Run Streamlit on a different port to avoid conflicts
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", str(app_path),
            "--server.address", "localhost",
            "--server.port", "8502",
            "--browser.gatherUsageStats", "false"
        ], cwd=project_root)
        
    except KeyboardInterrupt:
        print("\n🛑 Application stopped")
    except FileNotFoundError:
        print("\n❌ Error: Streamlit not found. Please install requirements:")
        print("   pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error starting application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()