#!/usr/bin/env python3
"""Quick Options Calculator Launcher"""

import subprocess
import sys
from pathlib import Path

def main():
    project_root = Path(__file__).parent
    app_path = project_root / "src" / "ui" / "quick_calc.py"
    
    print("⚡ Quick Options Calculator")
    print("🎯 Minimal interface for fast calculations")
    print("🌐 http://localhost:8503")
    print("=" * 40)
    
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", str(app_path),
            "--server.port", "8503",
            "--browser.gatherUsageStats", "false"
        ], cwd=project_root)
    except KeyboardInterrupt:
        print("\n🛑 Calculator stopped")

if __name__ == "__main__":
    main()