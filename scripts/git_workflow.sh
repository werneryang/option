#!/bin/bash
"""
Git Workflow Automation Script

Provides simple commands for common Git operations with automation.
"""

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if we're in a git repository
check_git_repo() {
    if [ ! -d ".git" ]; then
        print_error "Not a Git repository. Run 'git init' first."
        exit 1
    fi
}

# Initialize Git repository with best practices
init_repo() {
    print_info "Initializing Git repository..."
    
    if [ ! -d ".git" ]; then
        git init
        print_status "Git repository initialized"
    else
        print_info "Git repository already exists"
    fi
    
    # Set up default branch
    git config --local init.defaultBranch main
    
    # Set up user configuration (if not set globally)
    if [ -z "$(git config user.name)" ]; then
        read -p "Enter your name: " username
        git config --local user.name "$username"
    fi
    
    if [ -z "$(git config user.email)" ]; then
        read -p "Enter your email: " useremail
        git config --local user.email "$useremail"
    fi
    
    print_status "Git configuration complete"
}

# Quick commit with automatic message
quick_commit() {
    check_git_repo
    
    print_info "Running automated commit..."
    python scripts/auto_commit.py --auto
}

# Interactive commit
interactive_commit() {
    check_git_repo
    
    print_info "Running interactive commit..."
    python scripts/auto_commit.py
}

# Status with enhanced information
status() {
    check_git_repo
    
    print_info "Git Status:"
    git status --short
    
    echo ""
    print_info "Recent commits:"
    git log --oneline -5
    
    echo ""
    print_info "Branch information:"
    git branch -v
}

# Create and push a new feature branch
new_feature() {
    check_git_repo
    
    if [ -z "$1" ]; then
        print_error "Usage: $0 feature <branch-name>"
        exit 1
    fi
    
    branch_name="feature/$1"
    
    print_info "Creating feature branch: $branch_name"
    git checkout -b "$branch_name"
    
    print_status "Feature branch '$branch_name' created and checked out"
}

# Sync with remote
sync() {
    check_git_repo
    
    print_info "Syncing with remote..."
    
    # Fetch latest changes
    git fetch --all
    
    # Get current branch
    current_branch=$(git branch --show-current)
    
    # Pull latest changes for current branch
    if git rev-parse --verify "origin/$current_branch" >/dev/null 2>&1; then
        git pull origin "$current_branch"
        print_status "Synced with origin/$current_branch"
    else
        print_warning "No remote branch found for $current_branch"
    fi
}

# Push current branch
push() {
    check_git_repo
    
    current_branch=$(git branch --show-current)
    
    print_info "Pushing $current_branch to origin..."
    git push -u origin "$current_branch"
    
    print_status "Branch $current_branch pushed to origin"
}

# Create a release tag
release() {
    check_git_repo
    
    if [ -z "$1" ]; then
        print_error "Usage: $0 release <version>"
        print_info "Example: $0 release v1.0.0"
        exit 1
    fi
    
    version="$1"
    
    print_info "Creating release tag: $version"
    
    # Make sure we're on main/master
    current_branch=$(git branch --show-current)
    if [ "$current_branch" != "main" ] && [ "$current_branch" != "master" ]; then
        print_warning "Not on main/master branch. Switch first? (y/N)"
        read -r response
        if [ "$response" = "y" ] || [ "$response" = "Y" ]; then
            git checkout main 2>/dev/null || git checkout master
        fi
    fi
    
    # Create annotated tag
    git tag -a "$version" -m "Release $version"
    
    # Push tag
    git push origin "$version"
    
    print_status "Release $version created and pushed"
}

# Clean up merged branches
cleanup() {
    check_git_repo
    
    print_info "Cleaning up merged branches..."
    
    # Delete local branches that have been merged
    git branch --merged | grep -v "\*\|main\|master" | xargs -n 1 git branch -d
    
    # Prune remote tracking branches
    git remote prune origin
    
    print_status "Cleanup complete"
}

# Show help
show_help() {
    echo "Git Workflow Automation"
    echo "======================="
    echo ""
    echo "Usage: $0 <command> [arguments]"
    echo ""
    echo "Commands:"
    echo "  init                    Initialize Git repository"
    echo "  status                  Show enhanced Git status"
    echo "  commit                  Interactive automated commit"
    echo "  quick                   Quick automated commit"
    echo "  feature <name>          Create new feature branch"
    echo "  sync                    Sync with remote repository"
    echo "  push                    Push current branch to origin"
    echo "  release <version>       Create and push release tag"
    echo "  cleanup                 Clean up merged branches"
    echo "  help                    Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 init                 # Initialize repository"
    echo "  $0 quick                # Quick commit all changes"
    echo "  $0 feature new-ui       # Create feature/new-ui branch"
    echo "  $0 release v1.0.0       # Create v1.0.0 release"
}

# Main script logic
case "${1:-help}" in
    "init")
        init_repo
        ;;
    "status")
        status
        ;;
    "commit")
        interactive_commit
        ;;
    "quick")
        quick_commit
        ;;
    "feature")
        new_feature "$2"
        ;;
    "sync")
        sync
        ;;
    "push")
        push
        ;;
    "release")
        release "$2"
        ;;
    "cleanup")
        cleanup
        ;;
    "help"|*)
        show_help
        ;;
esac