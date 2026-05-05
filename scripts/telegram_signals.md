# Telegram Daily Signals

This script sends daily TradingAgents signals to Telegram.

## Prerequisites
- A Telegram bot token and chat ID
- LLM API key for your chosen provider

## Environment Variables

Required:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `SIGNAL_TICKERS` (comma-separated, e.g. `US500,US30,US100`)

Optional:
- `SIGNAL_TIME` (default `08:30`)
- `SIGNAL_TIMEZONE` (default `Africa/Kampala`)
- `LLM_PROVIDER` (default from config)
- `DEEP_THINK_LLM`
- `QUICK_THINK_LLM`
- `BACKEND_URL`
- `OUTPUT_LANGUAGE`
- `DATA_VENDOR_CORE`
- `DATA_VENDOR_INDICATORS`
- `DATA_VENDOR_FUNDAMENTALS`
- `DATA_VENDOR_NEWS`

## Run Once

```bash
python scripts/telegram_daily_signals.py --tickers "US500,US30,US100"
```

## Run Daily (Loop)

```bash
python scripts/telegram_daily_signals.py --loop --time 08:30 --timezone Africa/Kampala
```

## Dry Run (no LLM/Telegram)

```bash
python scripts/telegram_daily_signals.py --dry-run --tickers "US500,US30,US100"
```

## Cron Example (macOS)

```bash
# Every day at 08:30 Africa/Kampala (UTC+3 -> 05:30 UTC)
# Adjust UTC time if you want a different hour.
30 5 * * * cd /Users/edengilbert/Desktop/DEV/TradingAgents && /Users/edengilbert/Desktop/DEV/TradingAgents/.venv/bin/python scripts/telegram_daily_signals.py
```
