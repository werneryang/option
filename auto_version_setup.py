#!/usr/bin/env python3
"""
Auto Version Control Setup

Initialize automatic version control for the options analysis platform.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from src.utils.version_control import auto_version_control
from loguru import logger

def setup_auto_version_control():
    """Setup automatic version control system"""
    
    print("🔄 Setting up automatic version control...")
    print("=" * 60)
    
    try:
        # Initialize version control
        logger.info("Initializing automatic version control")
        
        # Get current status
        current_version = auto_version_control.get_current_version()
        print(f"📦 Current version: {current_version}")
        
        # Check git status
        git_status = auto_version_control._get_git_status()
        total_changes = len(git_status["untracked"]) + len(git_status["modified"])
        
        if total_changes > 0:
            print(f"📝 Found {total_changes} files with changes")
            
            # Classify changes
            all_files = git_status["untracked"] + git_status["modified"]
            classified = auto_version_control._classify_changes(all_files)
            
            for change_type, files in classified.items():
                if files:
                    print(f"   • {change_type}: {len(files)} files")
            
            # Perform initial auto-commit
            print("\n🚀 Performing initial auto-commit...")
            success = auto_version_control.auto_commit(force=False, version_level="minor")
            
            if success:
                new_version = auto_version_control.get_current_version()
                print(f"✅ Initial commit successful - Version: {new_version}")
            else:
                print("⚠️ Initial commit skipped (no changes)")
        
        else:
            print("✅ Working directory is clean")
        
        # Create initial backup branch
        print("\n💾 Creating initial backup...")
        backup_success = auto_version_control.create_backup_branch()
        
        if backup_success:
            print("✅ Initial backup branch created")
        else:
            print("⚠️ Backup branch creation skipped")
        
        print("\n🎯 Auto version control setup complete!")
        print("\n📋 Features enabled:")
        print("• Automatic commits without prompts")
        print("• Intelligent change classification")
        print("• Automatic version incrementing")
        print("• Changelog generation")
        print("• Backup branch creation")
        
        print("\n💡 Usage:")
        print("• Changes are automatically committed when detected")
        print("• Data updates trigger automatic commits")
        print("• Version numbers increment automatically")
        print("• Access via 'Version Control' page in the UI")
        
        return True
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        logger.error(f"Auto version control setup failed: {e}")
        return False

def main():
    """Main setup function"""
    print("🎯 Options Analysis Platform - Auto Version Control Setup")
    print("Setting up automatic version control without user prompts...")
    print()
    
    success = setup_auto_version_control()
    
    if success:
        print("\n✅ Setup completed successfully!")
        print("You can now use automatic version control features.")
    else:
        print("\n❌ Setup failed!")
        print("Please check the logs for more details.")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)