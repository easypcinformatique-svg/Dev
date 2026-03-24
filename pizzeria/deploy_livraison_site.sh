#!/bin/bash
# Deploy livraison-pizza-carpentras.fr to GitHub Pages
# Usage: bash deploy_livraison_site.sh

set -e

REPO_URL="https://github.com/easypcinformatique-svg/livraison-pizza-carpentras.git"
SITE_DIR="$(cd "$(dirname "$0")/livraison-site" && pwd)"
TEMP_DIR=$(mktemp -d)

echo "=== Deploying livraison-pizza-carpentras.fr ==="
echo "Source: $SITE_DIR"

# Clone or init the target repo
if git ls-remote "$REPO_URL" &>/dev/null; then
    echo "Cloning existing repo..."
    git clone "$REPO_URL" "$TEMP_DIR"
    cd "$TEMP_DIR"
    # Clean old files (keep .git)
    find . -maxdepth 1 ! -name '.git' ! -name '.' -exec rm -rf {} +
else
    echo "Initializing new repo..."
    cd "$TEMP_DIR"
    git init
    git remote add origin "$REPO_URL"
fi

# Copy site files
cp -r "$SITE_DIR"/* "$TEMP_DIR/"
cp "$SITE_DIR/CNAME" "$TEMP_DIR/" 2>/dev/null || true

# Commit and push
git add -A
git commit -m "Deploy livraison-pizza-carpentras.fr - $(date '+%Y-%m-%d %H:%M')" || echo "No changes to commit"
git branch -M main
git push -u origin main

echo ""
echo "=== Deploy OK ==="
echo ""
echo "Etapes suivantes :"
echo "1. Va sur https://github.com/easypcinformatique-svg/livraison-pizza-carpentras/settings/pages"
echo "2. Source: Deploy from a branch -> main -> / (root)"
echo "3. Save"
echo "4. Configure ton DNS chez ton registrar :"
echo "   - Type A : 185.199.108.153"
echo "   - Type A : 185.199.109.153"
echo "   - Type A : 185.199.110.153"
echo "   - Type A : 185.199.111.153"
echo "   - OU Type CNAME : livraison-pizza-carpentras.fr -> easypcinformatique-svg.github.io"
echo "5. Active 'Enforce HTTPS' dans les settings GitHub Pages"

# Cleanup
rm -rf "$TEMP_DIR"
