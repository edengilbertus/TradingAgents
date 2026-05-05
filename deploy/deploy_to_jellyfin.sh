#!/usr/bin/env bash
# ─────────────────────────────────────────────
#  Deploy Eden SMC Bot + TradingAgents AI Bias
#  Target: kacinema-jellyfin (159.89.104.10)
# ─────────────────────────────────────────────
#
#  Run this FROM YOUR LOCAL MAC:
#    bash deploy/deploy_to_jellyfin.sh
#
#  Prerequisites:
#    - SSH access to both droplets (root@134.209.127.52 and root@159.89.104.10)
#    - Your Gemini API key ready to paste into config.py
#
set -euo pipefail

CLAWTRADER_IP="134.209.127.52"
JELLYFIN_IP="159.89.104.10"
REMOTE_USER="root"
EDEN_USER="eden"
BOT_DIR="/home/eden/eden_bot"
TA_DIR="/home/eden/TradingAgents"
DEPLOY_DIR="$(cd "$(dirname "$0")" && pwd)/eden_bot"

echo "═══════════════════════════════════════════"
echo "  Eden Bot + TradingAgents Deployment"
echo "  From: Clawtrader ($CLAWTRADER_IP)"
echo "  To:   Kacinema-Jellyfin ($JELLYFIN_IP)"
echo "═══════════════════════════════════════════"
echo ""

# ── Step 1: Create eden user on jellyfin ──────
echo "=== Step 1: Setting up eden user on jellyfin ==="
ssh ${REMOTE_USER}@${JELLYFIN_IP} << 'REMOTE_SETUP'
    id -u eden &>/dev/null || useradd -m -s /bin/bash eden
    echo "User eden ready"
REMOTE_SETUP

# ── Step 2: Copy eden_bot from Clawtrader ─────
echo ""
echo "=== Step 2: Migrating eden_bot from Clawtrader ==="
echo "    Copying from Clawtrader → local → Jellyfin..."

# Create temp dir for migration
TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

# Pull from Clawtrader (exclude venv, pycache, logs)
rsync -avz --exclude 'venv/' --exclude '__pycache__/' --exclude 'logs/*.log' \
    ${REMOTE_USER}@${CLAWTRADER_IP}:${BOT_DIR}/ \
    "${TMPDIR}/eden_bot/"

echo "    Downloaded from Clawtrader ✓"

# ── Step 3: Overlay updated files ─────────────
echo ""
echo "=== Step 3: Applying integration files ==="
cp "${DEPLOY_DIR}/bot.py"              "${TMPDIR}/eden_bot/bot.py"
cp "${DEPLOY_DIR}/config.py"           "${TMPDIR}/eden_bot/config.py"
cp "${DEPLOY_DIR}/notifier.py"         "${TMPDIR}/eden_bot/notifier.py"
cp "${DEPLOY_DIR}/ai_bias.py"          "${TMPDIR}/eden_bot/ai_bias.py"
cp "${DEPLOY_DIR}/position_tracker.py" "${TMPDIR}/eden_bot/position_tracker.py"
echo "    Integration files applied ✓"

# ── Step 4: Push to Jellyfin ──────────────────
echo ""
echo "=== Step 4: Uploading to Jellyfin ==="
rsync -avz "${TMPDIR}/eden_bot/" ${REMOTE_USER}@${JELLYFIN_IP}:${BOT_DIR}/
echo "    Uploaded to Jellyfin ✓"

# ── Step 5: Clone TradingAgents + install ─────
echo ""
echo "=== Step 5: Installing TradingAgents ==="
ssh ${REMOTE_USER}@${JELLYFIN_IP} << REMOTE_INSTALL
    # Clone TradingAgents if not already present
    if [ ! -d "${TA_DIR}" ]; then
        cd /home/eden
        git clone https://github.com/TauricResearch/TradingAgents.git
        chown -R ${EDEN_USER}:${EDEN_USER} ${TA_DIR}
    else
        cd ${TA_DIR}
        git pull
    fi

    # Create venv and install deps
    cd ${BOT_DIR}
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    source venv/bin/activate

    # Install eden_bot requirements
    pip install -r requirements.txt 2>/dev/null || true

    # Install TradingAgents as editable package
    pip install -e ${TA_DIR}

    # Create data and logs dirs
    mkdir -p ${BOT_DIR}/data ${BOT_DIR}/logs

    # Fix ownership
    chown -R ${EDEN_USER}:${EDEN_USER} ${BOT_DIR}
    chown -R ${EDEN_USER}:${EDEN_USER} ${TA_DIR}

    echo "    TradingAgents installed ✓"
REMOTE_INSTALL

# ── Step 6: Set up systemd service ────────────
echo ""
echo "=== Step 6: Setting up systemd service ==="
ssh ${REMOTE_USER}@${JELLYFIN_IP} << 'REMOTE_SYSTEMD'
    cat > /etc/systemd/system/eden_bot.service << 'SERVICE'
[Unit]
Description=Eden SMC/ICT Bot + TradingAgents AI Bias
After=network.target

[Service]
Type=simple
User=eden
WorkingDirectory=/home/eden/eden_bot
ExecStart=/home/eden/eden_bot/venv/bin/python bot.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
SERVICE

    systemctl daemon-reload
    systemctl enable eden_bot
    echo "    Systemd service configured ✓"
REMOTE_SYSTEMD

# ── Done ──────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════"
echo "  ✅ Deployment complete!"
echo ""
echo "  BEFORE STARTING, you must:"
echo "  1. SSH into jellyfin and edit config.py:"
echo "     ssh root@${JELLYFIN_IP}"
echo "     nano ${BOT_DIR}/config.py"
echo "     → Replace YOUR_GEMINI_API_KEY_HERE"
echo ""
echo "  2. Start the bot:"
echo "     sudo systemctl start eden_bot"
echo ""
echo "  3. Check it's running:"
echo "     sudo systemctl status eden_bot"
echo "     journalctl -u eden_bot -f"
echo ""
echo "  4. Once verified, stop eden_bot on Clawtrader:"
echo "     ssh root@${CLAWTRADER_IP}"
echo "     sudo systemctl stop eden_bot"
echo "     sudo systemctl disable eden_bot"
echo "═══════════════════════════════════════════"
