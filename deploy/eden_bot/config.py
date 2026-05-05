# ─────────────────────────────────────────────
#  Eden SMC/ICT Bot — Configuration
# ─────────────────────────────────────────────

# ── Telegram ──────────────────────────────────
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID   = "YOUR_TELEGRAM_CHAT_ID"

# ── Twelve Data ───────────────────────────────
TWELVE_DATA_API_KEY = "YOUR_TWELVE_DATA_API_KEY"

# ── Google Sheets ─────────────────────────────
GOOGLE_SHEETS_CREDENTIALS_FILE = "credentials.json"   # service account JSON
GOOGLE_SHEET_ID = "YOUR_GOOGLE_SHEET_ID"         # from sheet URL

# ── AI Bias (TradingAgents) ───────────────────
GOOGLE_API_KEY    = "YOUR_GEMINI_API_KEY_HERE"   # ← Replace with your Gemini API key
AI_BIAS_ENABLED   = True
AI_BIAS_TIME_UTC  = "06:30"                      # Run before London kill zone
AI_LLM_PROVIDER   = "google"
AI_DEEP_MODEL     = "gemini-2.5-pro"             # Portfolio Manager + Research Manager
AI_QUICK_MODEL    = "gemini-2.5-flash"           # Analysts + Debaters

# ── Accounts (prop firm) ──────────────────────
ACCOUNTS = {
    "139625": {
        "name":            "5K Challenge",
        "starting_equity": 5_000.00,
        "equity":          5_071.33,
        "balance":         5_071.33,
        "max_loss_target": 318.18,
        "max_loss_remaining": 167.11,
        "max_loss_threshold":  4_904.22,
        "daily_loss_target":   202.85,
        "profit_target":       500.00,
        "profit_achieved":     71.33,
        "risk_per_trade":      0.01,   # 1%
    },
    "502208": {
        "name":            "2.5K Challenge",
        "starting_equity": 2_500.00,
        "equity":          2_500.90,
        "balance":         2_500.90,
        "max_loss_target": 250.00,
        "max_loss_remaining": 250.90,
        "max_loss_threshold":  2_250.00,
        "daily_loss_target":   125.05,
        "profit_target":       0.00,   # funded — already passed
        "profit_achieved":     0.90,
        "risk_per_trade":      0.01,   # 1%
    },
}

# ── Markets ───────────────────────────────────
SYMBOLS = {
    "NAS100": {"yf": "^NDX",  "td": "NDX",  "spread_pts": 2.0},
    "US30":   {"yf": "^DJI",  "td": "DJI",  "spread_pts": 3.0},
    "US500":  {"yf": "^GSPC", "td": "SPX",  "spread_pts": 0.5},
}
SMT_PAIR = ("NAS100", "US500")

# ── Strategy parameters ───────────────────────
HTF_SMA_PERIOD   = 20
OB_LOOKBACK      = 60
SWING_LOOKBACK   = 20
MIN_BODY_PCT     = 0.0008
OB_PROXIMITY_PCT = 0.008
MIN_CONFLUENCE   = 3
RR_RATIO         = 2.0
KILL_ZONE_DAYS   = {1, 2, 3}          # Mon=0 … Tue=1, Wed=2, Thu=3

# ── Sessions (UTC) ────────────────────────────
# London 02:00-05:00 ET  →  07:00-10:00 UTC
# New York 07:00-10:00 ET → 12:00-15:00 UTC
SESSIONS = [
    {"name": "London",   "start_utc": (7,  0), "end_utc": (10, 0)},
    {"name": "New York", "start_utc": (12, 0), "end_utc": (15, 0)},
]

# ── Scheduler ─────────────────────────────────
SCAN_INTERVAL_MINUTES  = 15     # how often to scan for signals
HOURLY_UPDATE_MINUTES  = 60     # how often to send hourly Telegram update
DATA_INTERVAL          = "15min"
HTF_INTERVAL           = "1day"
