#!/usr/bin/env python3
"""
Automated Git Commit Script

Automatically commits changes with meaningful commit messages
based on the types of changes detected.
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path
import re

def run_command(cmd, capture_output=True):
    """Run a shell command and return the result"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=capture_output, 
            text=True, check=False
        )
        return result.stdout.strip() if capture_output else result.returncode == 0
    except Exception as e:
        print(f"Error running command '{cmd}': {e}")
        return "" if capture_output else False

def get_git_status():
    """Get current git status"""
    status = run_command("git status --porcelain")
    return status.split('\n') if status else []

def analyze_changes(status_lines):
    """Analyze changes to determine commit message"""
    added_files = []
    modified_files = []
    deleted_files = []
    
    for line in status_lines:
        if not line:
            continue
        status_code = line[:2]
        filename = line[3:]
        
        if 'A' in status_code or '??' == status_code:
            added_files.append(filename)
        elif 'M' in status_code:
            modified_files.append(filename)
        elif 'D' in status_code:
            deleted_files.append(filename)
    
    return added_files, modified_files, deleted_files

def generate_commit_message(added, modified, deleted):
    """Generate meaningful commit message based on changes"""
    
    # Categorize changes
    categories = {
        'ui': [],
        'analytics': [],
        'data': [],
        'tests': [],
        'docs': [],
        'config': [],
        'scripts': []
    }
    
    all_files = added + modified + deleted
    
    for file in all_files:
        file_lower = file.lower()
        if 'ui/' in file_lower or 'streamlit' in file_lower or file_lower.endswith('.py') and 'app' in file_lower:
            categories['ui'].append(file)
        elif 'analytics/' in file_lower or 'black_scholes' in file_lower or 'strategies' in file_lower:
            categories['analytics'].append(file)
        elif 'data_sources/' in file_lower or 'storage' in file_lower or 'database' in file_lower:
            categories['data'].append(file)
        elif 'test' in file_lower or file_lower.endswith('_test.py'):
            categories['tests'].append(file)
        elif file_lower.endswith('.md') or 'readme' in file_lower or 'doc' in file_lower:
            categories['docs'].append(file)
        elif 'requirements' in file_lower or '.yml' in file_lower or 'config' in file_lower:
            categories['config'].append(file)
        elif 'script' in file_lower or file.startswith('run_'):
            categories['scripts'].append(file)
    
    # Generate message based on primary changes
    if categories['ui']:
        if added and any('ui/' in f for f in added):
            return "feat: add new UI components and interfaces"
        else:
            return "update: improve UI functionality and user experience"
    
    elif categories['analytics']:
        if added and any('analytics/' in f for f in added):
            return "feat: add new analytics capabilities"
        else:
            return "update: enhance analytics calculations and features"
    
    elif categories['data']:
        if added:
            return "feat: add data storage and processing capabilities"
        else:
            return "update: improve data handling and storage"
    
    elif categories['tests']:
        return "test: add/update test coverage and validation"
    
    elif categories['docs']:
        return "docs: update documentation and guides"
    
    elif categories['config']:
        return "config: update configuration and dependencies"
    
    elif categories['scripts']:
        return "scripts: add/update automation and utility scripts"
    
    # Fallback messages
    if added and not modified and not deleted:
        return f"feat: add {len(added)} new files"
    elif modified and not added and not deleted:
        return f"update: modify {len(modified)} files"
    elif deleted:
        return f"cleanup: remove {len(deleted)} files"
    else:
        return f"update: {len(added)} added, {len(modified)} modified, {len(deleted)} deleted"

def main():
    """Main automation function"""
    print("🤖 Automated Git Workflow")
    print("=" * 40)
    
    # Check if we're in a git repository
    if not Path('.git').exists():
        print("❌ Not a Git repository. Run 'git init' first.")
        return 1
    
    # Get current status
    status_lines = get_git_status()
    
    if not status_lines or not any(status_lines):
        print("✅ No changes to commit")
        return 0
    
    # Analyze changes
    added, modified, deleted = analyze_changes(status_lines)
    
    print(f"📊 Changes detected:")
    if added:
        print(f"  ➕ Added: {len(added)} files")
    if modified:
        print(f"  ✏️  Modified: {len(modified)} files")
    if deleted:
        print(f"  ❌ Deleted: {len(deleted)} files")
    
    # Generate commit message
    commit_message = generate_commit_message(added, modified, deleted)
    
    print(f"\n📝 Generated commit message:")
    print(f"   {commit_message}")
    
    # Add timestamp and signature
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    full_message = f"""{commit_message}

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"""
    
    # Confirm with user (optional - remove for full automation)
    if len(sys.argv) > 1 and sys.argv[1] == '--auto':
        proceed = True
    else:
        response = input("\n❓ Proceed with commit? (y/N): ").lower()
        proceed = response in ['y', 'yes']
    
    if not proceed:
        print("🛑 Commit cancelled")
        return 0
    
    # Stage all changes
    print("\n📦 Staging changes...")
    if not run_command("git add .", capture_output=False):
        print("❌ Failed to stage changes")
        return 1
    
    # Commit changes
    print("💾 Creating commit...")
    commit_cmd = f'git commit -m "{commit_message}" -m "🤖 Generated with [Claude Code](https://claude.ai/code)" -m "Co-Authored-By: Claude <noreply@anthropic.com>"'
    
    if not run_command(commit_cmd, capture_output=False):
        print("❌ Failed to create commit")
        return 1
    
    print("✅ Commit created successfully!")
    
    # Show recent commits
    print("\n📋 Recent commits:")
    recent_commits = run_command("git log --oneline -3")
    for line in recent_commits.split('\n'):
        if line:
            print(f"  {line}")
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)