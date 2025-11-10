#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SESSION_APP_DIR="$REPO_ROOT/frontend/session-app"
ADMIN_APP_DIR="$REPO_ROOT/frontend/admin-app"
SESSION_DIST="$SESSION_APP_DIR/dist"
ADMIN_DIST="$ADMIN_APP_DIR/dist"
NGINX_SITE_NAME="meetingpolice"
NGINX_AVAILABLE="/etc/nginx/sites-available/${NGINX_SITE_NAME}"
NGINX_ENABLED="/etc/nginx/sites-enabled/${NGINX_SITE_NAME}"

build_app () {
    local app_dir="$1"
    pushd "$app_dir" >/dev/null
    npm install
    npm run build
    popd >/dev/null
}

echo "Building session-app..."
build_app "$SESSION_APP_DIR"

echo "Building admin-app..."
build_app "$ADMIN_APP_DIR"

echo "Syncing build artifacts to /var/www..."
sudo mkdir -p /var/www/session-app /var/www/admin-app
sudo rsync -a --delete "$SESSION_DIST/" /var/www/session-app/
sudo rsync -a --delete "$ADMIN_DIST/" /var/www/admin-app/

echo "Deploying nginx configuration..."
sudo cp "$REPO_ROOT/nginx/default.conf" "$NGINX_AVAILABLE"
sudo ln -sf "$NGINX_AVAILABLE" "$NGINX_ENABLED"
if [[ -e /etc/nginx/sites-enabled/default ]]; then
    sudo rm /etc/nginx/sites-enabled/default
fi

echo "Reloading nginx..."
sudo nginx -t
sudo systemctl reload nginx

echo "Frontend build + nginx deployment complete."
echo "Update nginx/default.conf if SSL paths or document roots need customization."
