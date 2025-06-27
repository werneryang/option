"""
Automatic Version Control System

Provides automated version control for code, data, and configuration changes
without user confirmation prompts.
"""

import os
import subprocess
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from loguru import logger
import hashlib


class AutoVersionControl:
    """Automatic version control system without user prompts"""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent.parent
        self.version_file = self.project_root / "version.json"
        self.changes_log = self.project_root / "CHANGELOG.md"
        
        # Initialize git if not already done
        self._ensure_git_repo()
        self._load_version_info()
    
    def _ensure_git_repo(self):
        """Ensure git repository is initialized"""
        git_dir = self.project_root / ".git"
        if not git_dir.exists():
            try:
                subprocess.run(["git", "init"], cwd=self.project_root, capture_output=True, check=True)
                logger.info("Initialized git repository")
                
                # Create .gitignore if it doesn't exist
                gitignore_path = self.project_root / ".gitignore"
                if not gitignore_path.exists():
                    gitignore_content = """
# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.venv/
.env

# Data files
data/
exports/
logs/
*.log

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Temporary files
tmp/
temp/
*.tmp
"""
                    gitignore_path.write_text(gitignore_content.strip())
                    logger.info("Created .gitignore file")
                    
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to initialize git repository: {e}")
    
    def _load_version_info(self):
        """Load current version information"""
        try:
            if self.version_file.exists():
                with open(self.version_file, 'r') as f:
                    self.version_info = json.load(f)
            else:
                self.version_info = {
                    "major": 1,
                    "minor": 0,
                    "patch": 0,
                    "build": 0,
                    "last_updated": datetime.now().isoformat(),
                    "auto_commits": 0
                }
                self._save_version_info()
        except Exception as e:
            logger.error(f"Error loading version info: {e}")
            self.version_info = {
                "major": 1,
                "minor": 0,
                "patch": 0,
                "build": 0,
                "last_updated": datetime.now().isoformat(),
                "auto_commits": 0
            }
    
    def _save_version_info(self):
        """Save version information to file"""
        try:
            with open(self.version_file, 'w') as f:
                json.dump(self.version_info, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving version info: {e}")
    
    def get_current_version(self) -> str:
        """Get current version string"""
        return f"{self.version_info['major']}.{self.version_info['minor']}.{self.version_info['patch']}.{self.version_info['build']}"
    
    def _increment_version(self, level: str = "patch"):
        """Increment version number"""
        if level == "major":
            self.version_info["major"] += 1
            self.version_info["minor"] = 0
            self.version_info["patch"] = 0
        elif level == "minor":
            self.version_info["minor"] += 1
            self.version_info["patch"] = 0
        elif level == "patch":
            self.version_info["patch"] += 1
        
        self.version_info["build"] += 1
        self.version_info["last_updated"] = datetime.now().isoformat()
        self.version_info["auto_commits"] += 1
        self._save_version_info()
    
    def _get_git_status(self) -> Dict[str, List[str]]:
        """Get current git status"""
        try:
            # Get untracked files
            result = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            untracked = [f.strip() for f in result.stdout.split('\n') if f.strip()]
            
            # Get modified files
            result = subprocess.run(
                ["git", "diff", "--name-only"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            modified = [f.strip() for f in result.stdout.split('\n') if f.strip()]
            
            # Get staged files
            result = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            staged = [f.strip() for f in result.stdout.split('\n') if f.strip()]
            
            return {
                "untracked": untracked,
                "modified": modified,
                "staged": staged
            }
        except subprocess.CalledProcessError as e:
            logger.error(f"Error getting git status: {e}")
            return {"untracked": [], "modified": [], "staged": []}
    
    def _classify_changes(self, files: List[str]) -> Dict[str, List[str]]:
        """Classify file changes by type"""
        classified = {
            "code": [],
            "data": [],
            "config": [],
            "docs": [],
            "other": []
        }
        
        for file in files:
            if file.endswith(('.py', '.js', '.ts', '.html', '.css')):
                classified["code"].append(file)
            elif file.endswith(('.json', '.yaml', '.yml', '.toml', '.ini', '.env')):
                classified["config"].append(file)
            elif file.endswith(('.md', '.txt', '.rst')):
                classified["docs"].append(file)
            elif file.endswith(('.parquet', '.csv', '.sqlite', '.db')):
                classified["data"].append(file)
            else:
                classified["other"].append(file)
        
        return classified
    
    def _generate_commit_message(self, classified_changes: Dict[str, List[str]]) -> str:
        """Generate automatic commit message based on changes"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        version = self.get_current_version()
        
        message_parts = [f"auto: version {version} - {timestamp}"]
        
        for change_type, files in classified_changes.items():
            if files:
                count = len(files)
                if change_type == "code":
                    message_parts.append(f"• {count} code file{'s' if count > 1 else ''} updated")
                elif change_type == "data":
                    message_parts.append(f"• {count} data file{'s' if count > 1 else ''} updated")
                elif change_type == "config":
                    message_parts.append(f"• {count} config file{'s' if count > 1 else ''} updated")
                elif change_type == "docs":
                    message_parts.append(f"• {count} documentation file{'s' if count > 1 else ''} updated")
                elif change_type == "other":
                    message_parts.append(f"• {count} other file{'s' if count > 1 else ''} updated")
        
        return "\n".join(message_parts)
    
    def _update_changelog(self, version: str, changes: Dict[str, List[str]]):
        """Update changelog with new version"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            new_entry = f"\n## [{version}] - {timestamp}\n\n"
            
            for change_type, files in changes.items():
                if files:
                    new_entry += f"### {change_type.title()}\n"
                    for file in files[:10]:  # Limit to first 10 files
                        new_entry += f"- {file}\n"
                    if len(files) > 10:
                        new_entry += f"- ... and {len(files) - 10} more files\n"
                    new_entry += "\n"
            
            # Read existing changelog
            existing_content = ""
            if self.changes_log.exists():
                existing_content = self.changes_log.read_text()
            
            # If no changelog exists, create header
            if not existing_content:
                existing_content = "# Changelog\n\nAll notable changes to this project will be documented in this file.\n"
            
            # Insert new entry after header
            lines = existing_content.split('\n')
            header_end = 0
            for i, line in enumerate(lines):
                if line.startswith('## [') or i == len(lines) - 1:
                    header_end = i
                    break
            
            # Insert new entry
            lines.insert(header_end, new_entry)
            
            # Write back to file
            self.changes_log.write_text('\n'.join(lines))
            
        except Exception as e:
            logger.error(f"Error updating changelog: {e}")
    
    def auto_commit(self, force: bool = False, version_level: str = "patch") -> bool:
        """Automatically commit changes without prompts"""
        try:
            status = self._get_git_status()
            all_files = status["untracked"] + status["modified"]
            
            if not all_files and not force:
                logger.info("No changes to commit")
                return False
            
            # Classify changes
            classified_changes = self._classify_changes(all_files)
            
            # Add all files to staging
            if all_files:
                subprocess.run(
                    ["git", "add", "."],
                    cwd=self.project_root,
                    capture_output=True,
                    check=True
                )
                logger.info(f"Added {len(all_files)} files to staging")
            
            # Increment version
            self._increment_version(version_level)
            
            # Generate commit message
            commit_message = self._generate_commit_message(classified_changes)
            
            # Commit changes
            subprocess.run(
                ["git", "commit", "-m", commit_message],
                cwd=self.project_root,
                capture_output=True,
                check=True
            )
            
            # Update changelog
            self._update_changelog(self.get_current_version(), classified_changes)
            
            logger.info(f"✅ Auto-committed version {self.get_current_version()}")
            logger.info(f"📝 Commit message:\n{commit_message}")
            
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Error during auto-commit: {e}")
            return False
    
    def auto_commit_data_update(self, data_type: str, symbol: str = None) -> bool:
        """Automatically commit data updates"""
        try:
            # Custom commit message for data updates
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._increment_version("patch")
            version = self.get_current_version()
            
            if symbol:
                commit_message = f"data: update {data_type} for {symbol} - v{version}\n\n• Automated data collection\n• Timestamp: {timestamp}"
            else:
                commit_message = f"data: update {data_type} - v{version}\n\n• Automated data collection\n• Timestamp: {timestamp}"
            
            subprocess.run(
                ["git", "add", "data/"],
                cwd=self.project_root,
                capture_output=True,
                check=True
            )
            
            subprocess.run(
                ["git", "commit", "-m", commit_message],
                cwd=self.project_root,
                capture_output=True,
                check=True
            )
            
            logger.info(f"✅ Auto-committed data update: {data_type}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to commit data update: {e}")
            return False
    
    def get_commit_history(self, limit: int = 10) -> List[Dict[str, str]]:
        """Get recent commit history"""
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", f"-{limit}"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            
            commits = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split(' ', 1)
                    if len(parts) == 2:
                        commits.append({
                            "hash": parts[0],
                            "message": parts[1]
                        })
            
            return commits
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Error getting commit history: {e}")
            return []
    
    def create_backup_branch(self) -> bool:
        """Create backup branch with timestamp"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            branch_name = f"backup_{timestamp}"
            
            subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=self.project_root,
                capture_output=True,
                check=True
            )
            
            subprocess.run(
                ["git", "checkout", "main"],
                cwd=self.project_root,
                capture_output=True,
                check=True
            )
            
            logger.info(f"✅ Created backup branch: {branch_name}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create backup branch: {e}")
            return False


# Global instance
auto_version_control = AutoVersionControl()