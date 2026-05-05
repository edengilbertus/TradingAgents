# 🦅 Eden SMC/ICT Live Signal Bot

Runs 24/7 on Digital Ocean. Scans NAS100, US30, US500 every 15 minutes
during kill zones, sends Telegram signals, hourly updates, and logs everything
to Google Sheets.

---

## Architecture

```
Digital Ocean Droplet ($6/mo)
│
├── bot.py              ← main loop (scheduler)
├── scanner.py          ← SMC/ICT strategy logic (15-min candles)
├── data_feed.py        ← Twelve Data (15-min) + Yahoo Finance (HTF daily)
├── risk_manager.py     ← prop firm rules for both accounts
├── notifier.py         ← Telegram messages
├── sheets_logger.py    ← Google Sheets logging
└── config.py           ← all settings & credentials
```

---

## Step 1 — Telegram Bot Setup

1. Open Telegram → search **@BotFather**
2. Send `/newbot` → follow prompts → copy the **token**
3. Start a chat with your bot, then visit:
   `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
4. Send a message to the bot, refresh the URL → copy the **chat_id**
5. Paste both into `config.py`

---

## Step 2 — Twelve Data API Key

1. Go to https://twelvedata.com → sign up free
2. Dashboard → API Keys → copy your key
3. Paste into `config.py` as `TWELVE_DATA_API_KEY`

Free tier: 800 credits/day, 8/min — sufficient for 15-min scanning
(the bot only scans during kill zones, not 24/7)

---

## Step 3 — Google Sheets Setup

1. Go to https://console.cloud.google.com
2. Create a new project (e.g., "EdenBot")
3. Enable the **Google Sheets API** and **Google Drive API**
4. IAM → Service Accounts → Create service account
5. Keys → Add Key → JSON → download as `credentials.json`
6. Create a new Google Sheet, share it with the service account email
7. Copy the Sheet ID from the URL:
   `https://docs.google.com/spreadsheets/d/SHEET_ID_HERE/edit`
8. Paste `GOOGLE_SHEET_ID` in `config.py`
9. Place `credentials.json` in the bot folder

The bot auto-creates 3 tabs: **Signals**, **Hourly**, **Accounts**

---

## Step 4 — Digital Ocean Droplet

1. Create an account at https://digitalocean.com
2. Create Droplet → **Ubuntu 22.04** → **Basic $6/mo** (1GB RAM, 1 vCPU)
   - This is plenty for the bot
3. SSH into the droplet:
   ```bash
   ssh root@YOUR_DROPLET_IP
   ```
4. Upload files:
   ```bash
   # From your local machine:
   scp -r eden_bot/ root@YOUR_DROPLET_IP:/home/eden/
   scp credentials.json root@YOUR_DROPLET_IP:/home/eden/eden_bot/
   ```
5. Run setup:
   ```bash
   bash /home/eden/eden_bot/setup_droplet.sh
   ```
6. Edit config with your keys:
   ```bash
   nano /home/eden/eden_bot/config.py
   ```
7. Restart the bot:
   ```bash
   systemctl restart eden_bot
   ```

---

## Managing the Bot

| Command | What it does |
|---|---|
| `systemctl status eden_bot` | Check if running |
| `journalctl -u eden_bot -f` | Live logs |
| `systemctl restart eden_bot` | Restart |
| `systemctl stop eden_bot` | Stop |
| `tail -f logs/eden_bot.log` | File logs |

---

## What you'll receive on Telegram

**On a signal:**
```
📈 EDEN SMC SIGNAL
🟢 NAS100 — BULLISH
🕐 Session: London | 2026-03-25 08:15 UTC

📊 Entry:  18542.2500
🛑 Stop:   18488.1200
🎯 Target: 18650.5100

⚡ RR: 1:2 | Score: 4/5
📍 HTF Bias: BULLISH | Zone: DISCOUNT

Confluence:
  ✅ HTF aligned
  ✅ DISCOUNT zone
  ✅ SMT confirmed
  ✅ Strong OB (0.18%)
  ⚠️ OB proximity 0.412%

Position Sizing:
  🏦 5K Challenge (139625)
     Units: 0.0922  Risk: $50.71 (1.0%)
     Daily left: $202.85  Headroom: $167.11

  🏦 2.5K Challenge (502208)
     Units: 0.0462  Risk: $25.01 (1.0%)
     Daily left: $125.05  Headroom: $250.90
```

**Every hour:**
- Both account equity & profit progress
- Max loss consumed %
- Daily limit remaining
- Signals fired today

---

## Updating Account Equity

The account values in `config.py` are static — update them manually
after each trading day, or in a future version hook this up to your
broker's API for live equity tracking.

---

## Account Rules Encoded

| Rule | 5K Challenge | 2.5K Challenge |
|---|---|---|
| Max loss threshold | $4,904.22 | $2,250.00 |
| Daily loss limit | $202.85 | $125.05 |
| Profit target | $500.00 | Funded ✅ |
| Risk per trade | 1% | 1% |

The bot will **block** any trade that would use >80% of remaining
max loss headroom, or >90% of the daily loss limit.
