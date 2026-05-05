"""
bot.py — Eden SMC/ICT Live Signal Bot + TradingAgents AI Bias
        Runs 24/7 on Digital Ocean. Scans every 15 min in kill zones.
        Sends Telegram signals + hourly updates + daily AI bias.
        Logs to Google Sheets.

Usage:
    python bot.py
"""

import logging
import time
import schedule
from datetime import datetime, timezone

from config import ACCOUNTS, SCAN_INTERVAL_MINUTES, HOURLY_UPDATE_MINUTES
from config import AI_BIAS_ENABLED, AI_BIAS_TIME_UTC
from data_feed import get_all_data
from scanner import scan_all, in_kill_zone
from risk_manager import build_trade_plan, account_summary
from notifier import (send_signal, send_hourly_update, send_startup,
                      send_error, send_no_signal_in_session,
                      send_ai_daily_bias, get_ai_alignment_tag)
from sheets_logger import log_signal, log_hourly, log_account_snapshot

# ─────────────────────────────────────────────
#  Logging setup
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s — %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/eden_bot.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger("eden.bot")

# ─────────────────────────────────────────────
#  State
# ─────────────────────────────────────────────
signals_today: list[dict] = []
last_session_scanned: str = ""
daily_ai_biases: dict = {}           # ← NEW: stores today's AI bias per symbol


def _get_summaries() -> list[dict]:
    return [account_summary(acc_id) for acc_id in ACCOUNTS]


# ─────────────────────────────────────────────
#  AI Bias job (NEW — runs daily at 06:30 UTC)
# ─────────────────────────────────────────────

def run_ai_bias() -> None:
    """Run TradingAgents AI analysis and send daily bias to Telegram."""
    global daily_ai_biases
    logger.info("=== Running AI daily bias ===")

    try:
        from ai_bias import get_daily_biases
        from position_tracker import update_bias

        biases = get_daily_biases()
        daily_ai_biases = biases

        # Track bias changes for position monitoring
        changes = []
        for symbol, bias in biases.items():
            if bias.get("rating") != "ERROR":
                change = update_bias(symbol, bias["rating"])
                changes.append(change)

        send_ai_daily_bias(biases, changes)
        logger.info("AI bias sent: %s", {s: b["rating"] for s, b in biases.items()})

    except Exception as e:
        logger.exception("AI bias error: %s", e)
        send_error("run_ai_bias", str(e))


# ─────────────────────────────────────────────
#  Scan job (every 15 min)
# ─────────────────────────────────────────────

def run_scan() -> None:
    global last_session_scanned
    now = datetime.now(timezone.utc)
    in_kz, session_name = in_kill_zone(now)

    if not in_kz:
        logger.debug("Outside kill zone at %s UTC — scan skipped", now.strftime("%H:%M"))
        return

    logger.info("=== Kill zone scan: %s ===", session_name)

    try:
        data = get_all_data()
        if not data:
            logger.error("No data fetched — aborting scan")
            send_error("run_scan", "get_all_data() returned empty — check API keys / network")
            return

        signals = scan_all(data)

        if not signals:
            # Only notify once per session (not every 15-min interval)
            if session_name != last_session_scanned:
                send_no_signal_in_session(session_name, len(data))
                last_session_scanned = session_name
            return

        for signal in signals:
            # Deduplicate: skip if same symbol + direction + entry already sent today
            already_sent = any(
                s["symbol"]    == signal["symbol"]
                and s["direction"] == signal["direction"]
                and s["entry"]     == signal["entry"]
                for s in signals_today
            )
            if already_sent:
                logger.info(
                    "Duplicate signal skipped: %s %s entry=%.4f",
                    signal["symbol"], signal["direction"].upper(), signal["entry"]
                )
                continue

            plans = build_trade_plan(signal)

            # ── NEW: Get AI alignment tag ──
            ai_alignment = get_ai_alignment_tag(
                daily_ai_biases,
                signal["symbol"],
                signal["direction"],   # "bullish" or "bearish"
            )

            send_signal(signal, plans, ai_alignment=ai_alignment)
            log_signal(signal, plans)
            signals_today.append(signal)

        last_session_scanned = session_name

    except Exception as e:
        logger.exception("Scan error: %s", e)
        send_error("run_scan", str(e))


# ─────────────────────────────────────────────
#  Hourly update job
# ─────────────────────────────────────────────

def run_hourly_update() -> None:
    logger.info("Sending hourly update")
    try:
        summaries = _get_summaries()
        last_sig  = signals_today[-1] if signals_today else None
        send_hourly_update(summaries, len(signals_today), last_sig)
        log_hourly(summaries, len(signals_today))
        log_account_snapshot(summaries)
    except Exception as e:
        logger.exception("Hourly update error: %s", e)
        send_error("run_hourly_update", str(e))


# ─────────────────────────────────────────────
#  Daily reset (midnight UTC)
# ─────────────────────────────────────────────

def daily_reset() -> None:
    global signals_today, last_session_scanned, daily_ai_biases
    logger.info("Daily reset — clearing today's signal log and AI biases")
    signals_today = []
    last_session_scanned = ""
    daily_ai_biases = {}


# ─────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────

def main() -> None:
    logger.info("Eden SMC Bot starting up...")
    send_startup()

    # Schedule scan every 15 minutes
    schedule.every(SCAN_INTERVAL_MINUTES).minutes.do(run_scan)

    # Hourly update
    schedule.every(HOURLY_UPDATE_MINUTES).minutes.do(run_hourly_update)

    # Daily reset at midnight UTC
    schedule.every().day.at("00:00").do(daily_reset)

    # ── NEW: Daily AI bias before London kill zone ──
    if AI_BIAS_ENABLED:
        schedule.every().day.at(AI_BIAS_TIME_UTC).do(run_ai_bias)
        logger.info("AI bias scheduled daily at %s UTC", AI_BIAS_TIME_UTC)

    # Run an immediate scan on startup if in kill zone
    run_scan()

    # Run an immediate hourly update on startup
    run_hourly_update()

    logger.info(
        "Scheduler running — scan every %d min, hourly update every %d min, AI bias daily at %s UTC",
        SCAN_INTERVAL_MINUTES, HOURLY_UPDATE_MINUTES, AI_BIAS_TIME_UTC
    )

    while True:
        try:
            schedule.run_pending()
            time.sleep(30)
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            break
        except Exception as e:
            logger.exception("Main loop error: %s", e)
            send_error("main_loop", str(e))
            time.sleep(60)  # brief pause then continue


if __name__ == "__main__":
    main()
