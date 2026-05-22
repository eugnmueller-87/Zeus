#!/bin/bash
# ============================================================
# Pantheon OS — Hetzner CX21 Bootstrap Script
# Run once as root on a fresh Ubuntu 24.04 server
#
# Usage:
#   ssh root@YOUR_SERVER_IP
#   curl -fsSL https://raw.githubusercontent.com/eugnmueller-87/Pantheon/main/infra/hetzner/setup.sh | bash
# ============================================================

set -euo pipefail

DOMAIN="${DOMAIN:-YOUR_DOMAIN}"
GITHUB_REPO="ghcr.io/eugnmueller-87/pantheon"
APP_DIR="/opt/pantheon"
APP_USER="pantheon"

echo "============================================================"
echo " Pantheon OS — Server Bootstrap"
echo " Domain: $DOMAIN"
echo "============================================================"

# ── 1. System update ──────────────────────────────────────────
apt-get update -qq && apt-get upgrade -y -qq

# ── 2. Docker ─────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl enable --now docker
fi

# ── 3. Docker Compose plugin ──────────────────────────────────
apt-get install -y -qq docker-compose-plugin

# ── 4. Certbot (SSL) ──────────────────────────────────────────
apt-get install -y -qq certbot python3-certbot-nginx

# ── 5. App user + directory ───────────────────────────────────
useradd -r -s /bin/false "$APP_USER" 2>/dev/null || true
mkdir -p "$APP_DIR"
chown "$APP_USER:$APP_USER" "$APP_DIR"

# ── 6. GitHub Container Registry login ───────────────────────
# Requires GHCR_TOKEN env var set before running this script
if [ -n "${GHCR_TOKEN:-}" ]; then
    echo "$GHCR_TOKEN" | docker login ghcr.io -u eugnmueller-87 --password-stdin
fi

# ── 7. UFW firewall ───────────────────────────────────────────
apt-get install -y -qq ufw
ufw --force enable
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
echo "UFW configured."

# ── 8. Certbot SSL cert ───────────────────────────────────────
if [ "$DOMAIN" != "YOUR_DOMAIN" ]; then
    certbot certonly --standalone \
        --non-interactive \
        --agree-tos \
        --email "eugnmueller@googlemail.com" \
        --domain "$DOMAIN" \
        || echo "Certbot failed — run manually after DNS propagates."

    # Auto-renew cron
    (crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet && docker compose -f $APP_DIR/docker-compose.prod.yml restart nginx") | crontab -
fi

# ── 9. Systemd service ────────────────────────────────────────
cat > /etc/systemd/system/pantheon.service << EOF
[Unit]
Description=Pantheon OS Trading System
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$APP_DIR
ExecStart=/usr/bin/docker compose -f docker-compose.prod.yml up -d
ExecStop=/usr/bin/docker compose -f docker-compose.prod.yml down
TimeoutStartSec=120

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable pantheon

# ── 10. Deploy script ─────────────────────────────────────────
cat > "$APP_DIR/deploy.sh" << 'EOF'
#!/bin/bash
# Run to pull latest image and restart
set -euo pipefail
cd /opt/pantheon
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d --remove-orphans
docker image prune -f
echo "Deployed at $(date)"
EOF
chmod +x "$APP_DIR/deploy.sh"

echo ""
echo "============================================================"
echo " Bootstrap complete."
echo ""
echo " Next steps:"
echo "   1. Copy your .env file:  scp .env root@$DOMAIN:/opt/pantheon/.env"
echo "   2. Copy compose file:    scp infra/hetzner/docker-compose.prod.yml root@$DOMAIN:/opt/pantheon/"
echo "   3. Copy nginx config:    scp infra/hetzner/nginx.prod.conf root@$DOMAIN:/opt/pantheon/nginx.prod.conf"
echo "      (then update YOUR_DOMAIN in nginx.prod.conf)"
echo "   4. Start:                systemctl start pantheon"
echo "   5. Check logs:           docker compose -f /opt/pantheon/docker-compose.prod.yml logs -f"
echo "============================================================"
