"""Send daily TradingAgents signals to Telegram.

Usage examples:
  # Run once (real signals)
  python scripts/telegram_daily_signals.py --tickers "US500,US30,US100"

  # Dry run (no LLM calls, no Telegram send)
  python scripts/telegram_daily_signals.py --dry-run --tickers "US500,US30,US100"

  # Run daily at 08:30 Africa/Kampala
  python scripts/telegram_daily_signals.py --loop --time 08:30 --timezone Africa/Kampala
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timedelta, time as dt_time
from typing import Iterable
from zoneinfo import ZoneInfo

import requests

from tradingagents.default_config import DEFAULT_CONFIG


def _parse_tickers(raw: str) -> list[str]:
    if not raw:
        return []
    parts = [p.strip() for p in raw.replace(";", ",").replace(" ", ",").split(",")]
    return [p for p in parts if p]


def _parse_time(value: str) -> dt_time:
    try:
        hour, minute = value.split(":", 1)
        return dt_time(hour=int(hour), minute=int(minute))
    except Exception as exc:
        raise ValueError("Time must be in HH:MM format") from exc


def _next_run(now: datetime, run_time: dt_time) -> datetime:
    candidate = now.replace(hour=run_time.hour, minute=run_time.minute, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


def _build_config() -> dict:
    config = DEFAULT_CONFIG.copy()
    config["llm_provider"] = os.getenv("LLM_PROVIDER", config["llm_provider"])
    config["deep_think_llm"] = os.getenv("DEEP_THINK_LLM", config["deep_think_llm"])
    config["quick_think_llm"] = os.getenv("QUICK_THINK_LLM", config["quick_think_llm"])
    config["backend_url"] = os.getenv("BACKEND_URL", config["backend_url"])
    config["output_language"] = os.getenv("OUTPUT_LANGUAGE", config["output_language"])

    vendor_overrides = {
        "core_stock_apis": os.getenv("DATA_VENDOR_CORE"),
        "technical_indicators": os.getenv("DATA_VENDOR_INDICATORS"),
        "fundamental_data": os.getenv("DATA_VENDOR_FUNDAMENTALS"),
        "news_data": os.getenv("DATA_VENDOR_NEWS"),
    }
    for key, value in vendor_overrides.items():
        if value:
            config["data_vendors"][key] = value

    return config


def _send_telegram_message(token: str, chat_id: str, message: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(url, json={"chat_id": chat_id, "text": message})
    resp.raise_for_status()


def _format_message(date_str: str, tz_name: str, results: Iterable[tuple[str, str]]) -> str:
    lines = [f"TradingAgents signals for {date_str} ({tz_name})", ""]
    for ticker, decision in results:
        lines.append(f"- {ticker}: {decision}")
    return "\n".join(lines)


def _run_once(tickers: list[str], tz: ZoneInfo, dry_run: bool) -> str:
    run_date = datetime.now(tz=tz).date().isoformat()
    if dry_run:
        results = [(t, "HOLD") for t in tickers]
        return _format_message(run_date, tz.key, results)

    # Heavy imports are delayed so dry-run starts fast.
    from tradingagents.graph.trading_graph import TradingAgentsGraph

    config = _build_config()
    graph = TradingAgentsGraph(debug=False, config=config)

    results = []
    for ticker in tickers:
        try:
            _state, decision = graph.propagate(ticker, run_date)
            results.append((ticker, decision))
        except Exception as exc:
            results.append((ticker, f"ERROR: {exc}"))

    return _format_message(run_date, tz.key, results)


def main() -> int:
    parser = argparse.ArgumentParser(description="Send daily TradingAgents signals to Telegram.")
    parser.add_argument("--tickers", default=os.getenv("SIGNAL_TICKERS", ""))
    parser.add_argument("--time", dest="run_time", default=os.getenv("SIGNAL_TIME", "08:30"))
    parser.add_argument("--timezone", default=os.getenv("SIGNAL_TIMEZONE", "Africa/Kampala"))
    parser.add_argument("--loop", action="store_true", help="Run daily at the scheduled time")
    parser.add_argument("--dry-run", action="store_true", help="Skip LLM and Telegram calls")
    args = parser.parse_args()

    tickers = _parse_tickers(args.tickers)
    if not tickers:
        print("No tickers provided. Use --tickers or SIGNAL_TICKERS.")
        return 2

    tz = ZoneInfo(args.timezone)
    run_time = _parse_time(args.run_time)

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not args.dry_run and (not token or not chat_id):
        print("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID.")
        return 2

    def send_once() -> None:
        message = _run_once(tickers, tz, args.dry_run)
        if args.dry_run:
            print(message)
        else:
            _send_telegram_message(token, chat_id, message)
            print("Signal sent.")

    if not args.loop:
        send_once()
        return 0

    while True:
        now = datetime.now(tz=tz)
        next_run = _next_run(now, run_time)
        sleep_for = (next_run - now).total_seconds()
        print(f"Next run at {next_run.isoformat()} ({tz.key}).")
        time.sleep(max(sleep_for, 1))
        send_once()


if __name__ == "__main__":
    raise SystemExit(main())
