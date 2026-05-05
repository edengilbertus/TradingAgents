#!/bin/bash
# ─────────────────────────────────────────────────────
#  Eden SMC Bot — Digital Ocean Droplet Setup
#  Run once as root on a fresh Ubuntu 22.04 droplet
#  Smallest droplet ($6/mo, 1GB RAM) is fine.
# ─────────────────────────────────────────────────────

set -e

echo "=== 1. System update ==="
apt update && apt upgrade -y
apt install -y python3 python3-pip python3-venv git curl

echo "=== 2. Create non-root user ==="
useradd -m -s /bin/bash eden || echo "User 'eden' already exists"
mkdir -p /home/eden/eden_bot/logs /home/eden/eden_bot/data
chown -R eden:eden /home/eden/eden_bot

echo "=== 3. Copy bot files ==="
# (Run this from your local machine first — adjust path as needed)
# scp -r ./eden_bot/* root@YOUR_DROPLET_IP:/home/eden/eden_bot/
# scp credentials.json root@YOUR_DROPLET_IP:/home/eden/eden_bot/

echo "=== 4. Create virtualenv & install deps ==="
cd /home/eden/eden_bot
python3 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt
chown -R eden:eden /home/eden/eden_bot

echo "=== 5. Edit config.py with your API keys ==="
echo "  nano /home/eden/eden_bot/config.py"
echo ""
echo "  Fill in:"
echo "    TELEGRAM_BOT_TOKEN"
echo "    TELEGRAM_CHAT_ID"
echo "    TWELVE_DATA_API_KEY"
echo "    GOOGLE_SHEET_ID"
echo "  Also place credentials.json in /home/eden/eden_bot/"

echo "=== 6. Install systemd service ==="
cp /home/eden/eden_bot/eden_bot.service /etc/systemd/system/eden_bot.service
systemctl daemon-reload
systemctl enable eden_bot
systemctl start eden_bot

echo ""
echo "=== Done! ==="
echo ""
echo "Useful commands:"
echo "  systemctl status eden_bot        # check if running"
echo "  journalctl -u eden_bot -f        # live logs"
echo "  systemctl restart eden_bot       # restart"
echo "  systemctl stop eden_bot          # stop"
echo ""
echo "Log file: /home/eden/eden_bot/logs/eden_bot.log"
