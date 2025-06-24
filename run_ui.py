#!/usr/bin/env python3
"""
Options Analysis Platform UI Launcher

Simple script to launch the Streamlit web application.
Ensures proper path setup and provides user guidance.
"""

import subprocess
import sys
from pathlib import Path

def main():
    """Launch the Streamlit application"""
    
    # Get the project root directory
    project_root = Path(__file__).parent
    
    # Path to the Streamlit app
    app_path = project_root / "src" / "ui" / "main_application.py"
    
    if not app_path.exists():
        print("❌ Error: Streamlit app not found at", app_path)
        print("Make sure you're running this from the project root directory.")
        sys.exit(1)
    
    print("🚀 Starting Options Analysis Platform...")
    print(f"📁 Project root: {project_root}")
    print(f"🎯 App path: {app_path}")
    print()
    print("🌐 The application will open in your web browser.")
    print("📊 Navigate using the sidebar to access different features:")
    print("   • Dashboard - Overview and key metrics")
    print("   • Option Chain - Interactive option chain analysis")
    print("   • Strategy Builder - Create and analyze options strategies")
    print("   • Analytics - Advanced analysis tools")
    print()
    print("⏹️  Press Ctrl+C to stop the application")
    print("=" * 60)
    
    try:
        # Run Streamlit
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", str(app_path),
            "--server.address", "localhost",
            "--server.port", "8501",
            "--browser.gatherUsageStats", "false"
        ], cwd=project_root)
        
    except KeyboardInterrupt:
        print("\n🛑 Application stopped by user")
    except FileNotFoundError:
        print("\n❌ Error: Streamlit not found. Please install requirements:")
        print("   pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error starting application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()