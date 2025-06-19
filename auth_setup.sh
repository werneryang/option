#!/bin/bash
# GitHub Authentication Setup Helper

echo "🔐 GitHub Authentication Setup"
echo "=============================="
echo ""
echo "Choose your authentication method:"
echo ""
echo "1. Personal Access Token (Recommended)"
echo "2. GitHub CLI (Easiest)"
echo "3. SSH Key (Most Secure)"
echo ""
read -p "Enter your choice (1-3): " choice

case $choice in
    1)
        echo ""
        echo "📝 Personal Access Token Setup:"
        echo "1. Go to: https://github.com/settings/tokens"
        echo "2. Click 'Generate new token (classic)'"
        echo "3. Select scopes: 'repo' and 'workflow'"
        echo "4. Copy the generated token"
        echo ""
        echo "Then run: git push -u origin main"
        echo "Username: werneryang"
        echo "Password: <paste-your-token>"
        ;;
    2)
        echo ""
        echo "🚀 GitHub CLI Setup:"
        if command -v gh &> /dev/null; then
            echo "GitHub CLI is installed!"
            echo "Running authentication..."
            gh auth login
            echo ""
            echo "Now running: git push -u origin main"
            git push -u origin main
        else
            echo "Installing GitHub CLI..."
            if command -v brew &> /dev/null; then
                brew install gh
                echo "Now run: gh auth login"
                echo "Then: git push -u origin main"
            else
                echo "Please install GitHub CLI from: https://cli.github.com/"
                echo "Then run: gh auth login && git push -u origin main"
            fi
        fi
        ;;
    3)
        echo ""
        echo "🔑 SSH Key Setup:"
        echo "1. Generate SSH key:"
        echo "   ssh-keygen -t ed25519 -C \"your-email@example.com\""
        echo ""
        echo "2. Add to SSH agent:"
        echo "   eval \"\$(ssh-agent -s)\""
        echo "   ssh-add ~/.ssh/id_ed25519"
        echo ""
        echo "3. Copy public key:"
        echo "   cat ~/.ssh/id_ed25519.pub"
        echo ""
        echo "4. Add to GitHub:"
        echo "   Go to: https://github.com/settings/ssh"
        echo "   Click 'New SSH key' and paste the public key"
        echo ""
        echo "5. Update remote and push:"
        echo "   git remote set-url origin git@github.com:werneryang/option.git"
        echo "   git push -u origin main"
        ;;
    *)
        echo "Invalid choice. Please run the script again."
        ;;
esac