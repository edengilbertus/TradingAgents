"""
data_feed.py — Dual data source: Yahoo Finance (daily HTF) + Twelve Data (15-min intraday)
Falls back to Yahoo Finance if Twelve Data fails or rate-limits.
"""

import time
import logging
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta, timezone
from config import TWELVE_DATA_API_KEY, SYMBOLS

logger = logging.getLogger("eden.data")


# ─────────────────────────────────────────────
#  Twelve Data  (15-min intraday)
# ─────────────────────────────────────────────

TD_BASE = "https://api.twelvedata.com"

def _td_get(endpoint: str, params: dict) -> dict | None:
    params["apikey"] = TWELVE_DATA_API_KEY
    try:
        r = requests.get(f"{TD_BASE}/{endpoint}", params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        if data.get("status") == "error":
            logger.warning("Twelve Data error: %s", data.get("message"))
            return None
        return data
    except Exception as e:
        logger.error("Twelve Data request failed: %s", e)
        return None


def fetch_intraday_td(symbol: str, interval: str = "15min", bars: int = 200) -> pd.DataFrame | None:
    """Fetch intraday OHLCV from Twelve Data."""
    td_sym = SYMBOLS[symbol]["td"]
    data = _td_get("time_series", {
        "symbol":    td_sym,
        "interval":  interval,
        "outputsize": bars,
        "timezone":  "UTC",
        "order":     "ASC",
    })
    if not data or "values" not in data:
        return None
    df = pd.DataFrame(data["values"])
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.set_index("datetime").rename(columns={
        "open": "Open", "high": "High", "low": "Low",
        "close": "Close", "volume": "Volume"
    })
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.dropna()


# ─────────────────────────────────────────────
#  Yahoo Finance  (daily HTF bias + fallback)
# ─────────────────────────────────────────────

def fetch_daily_yf(symbol: str, days: int = 100) -> pd.DataFrame | None:
    """Fetch daily OHLCV from Yahoo Finance for HTF bias."""
    yf_sym = SYMBOLS[symbol]["yf"]
    end   = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    try:
        df = yf.download(yf_sym, start=start, end=end, interval="1d",
                         progress=False, auto_adjust=True)
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
        df.index = pd.to_datetime(df.index)
        return df
    except Exception as e:
        logger.error("Yahoo Finance fetch failed for %s: %s", symbol, e)
        return None


def fetch_intraday_yf_fallback(symbol: str, interval: str = "15m", days: int = 55) -> pd.DataFrame | None:
    """Fallback 15-min data from Yahoo Finance (limited to ~60 days free)."""
    yf_sym = SYMBOLS[symbol]["yf"]
    end   = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    try:
        df = yf.download(yf_sym, start=start, end=end, interval=interval,
                         progress=False, auto_adjust=True)
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
        df.index = pd.to_datetime(df.index)
        return df
    except Exception as e:
        logger.error("YF intraday fallback failed for %s: %s", symbol, e)
        return None


# ─────────────────────────────────────────────
#  Public interface
# ─────────────────────────────────────────────

def get_intraday(symbol: str, bars: int = 200) -> pd.DataFrame | None:
    """Get 15-min data — tries Twelve Data first, falls back to Yahoo Finance."""
    df = fetch_intraday_td(symbol, bars=bars)
    if df is not None and len(df) >= 50:
        logger.debug("%s: 15-min data from Twelve Data (%d bars)", symbol, len(df))
        return df
    logger.warning("%s: Twelve Data failed, falling back to Yahoo Finance", symbol)
    time.sleep(0.5)
    return fetch_intraday_yf_fallback(symbol)


def get_daily(symbol: str, days: int = 100) -> pd.DataFrame | None:
    """Get daily data from Yahoo Finance for HTF bias."""
    return fetch_daily_yf(symbol, days=days)


def get_all_data() -> dict:
    """Fetch both daily and 15-min data for all symbols. Returns dict of dicts."""
    result = {}
    for sym in SYMBOLS:
        daily    = get_daily(sym)
        intraday = get_intraday(sym)
        if daily is None or intraday is None:
            logger.error("Could not fetch data for %s — skipping", sym)
            continue
        result[sym] = {"daily": daily, "intraday": intraday}
        time.sleep(0.3)   # be gentle on APIs
    return result
