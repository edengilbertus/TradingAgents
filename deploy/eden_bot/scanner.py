"""
scanner.py — Eden SMC/ICT strategy logic running on 15-min candles
              with daily HTF bias filter.
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timezone

from config import (
    HTF_SMA_PERIOD, OB_LOOKBACK, SWING_LOOKBACK, MIN_BODY_PCT,
    OB_PROXIMITY_PCT, MIN_CONFLUENCE, KILL_ZONE_DAYS, SESSIONS, SMT_PAIR
)

logger = logging.getLogger("eden.scanner")


# ─────────────────────────────────────────────
#  Session helpers
# ─────────────────────────────────────────────

def in_kill_zone(dt: datetime) -> tuple[bool, str]:
    """Return (True, session_name) if dt falls inside a configured session window."""
    if dt.weekday() not in KILL_ZONE_DAYS:
        return False, ""
    utc_h, utc_m = dt.hour, dt.minute
    for s in SESSIONS:
        sh, sm = s["start_utc"]
        eh, em = s["end_utc"]
        start_mins = sh * 60 + sm
        end_mins   = eh * 60 + em
        now_mins   = utc_h * 60 + utc_m
        if start_mins <= now_mins < end_mins:
            return True, s["name"]
    return False, ""


# ─────────────────────────────────────────────
#  HTF bias (daily SMA)
# ─────────────────────────────────────────────

def get_htf_bias(daily_df: pd.DataFrame) -> str:
    if daily_df is None or len(daily_df) < HTF_SMA_PERIOD:
        return "NEUTRAL"
    closes = daily_df["Close"]
    sma    = closes.iloc[-HTF_SMA_PERIOD:].mean()
    cur    = closes.iloc[-1]
    if cur > sma * 1.002:  return "BULLISH"
    if cur < sma * 0.998:  return "BEARISH"
    return "NEUTRAL"


# ─────────────────────────────────────────────
#  PD Zone (Premium / Discount / Equilibrium)
# ─────────────────────────────────────────────

def get_pd_zone(df: pd.DataFrame, price: float) -> str:
    w = df.iloc[-SWING_LOOKBACK:]
    if len(w) < 5:
        return "NEUTRAL"
    hi = w["High"].max()
    lo = w["Low"].min()
    if hi == lo:
        return "NEUTRAL"
    eq = (hi + lo) / 2
    if price < eq * 0.999:  return "DISCOUNT"
    if price > eq * 1.001:  return "PREMIUM"
    return "EQUILIBRIUM"


# ─────────────────────────────────────────────
#  Order Block detection
# ─────────────────────────────────────────────

def find_order_block(df: pd.DataFrame, direction: str) -> dict | None:
    """Scan backwards from the current bar for an unmitigated OB."""
    idx = len(df) - 1
    start = max(0, idx - OB_LOOKBACK)

    for i in range(idx - 4, start, -1):
        o  = df["Open"].iloc[i]
        h  = df["High"].iloc[i]
        lo = df["Low"].iloc[i]
        cl = df["Close"].iloc[i]
        if o == 0 or abs(cl - o) / o < MIN_BODY_PCT:
            continue
        body_pct = abs(cl - o) / o
        nxt  = df.iloc[i + 1: i + 4]
        subq = df.iloc[i + 4: idx + 1]
        if len(nxt) < 3:
            continue

        if direction == "bullish":
            if cl >= o:                                          continue
            if not (nxt["High"].max() > h and nxt["Close"].iloc[-1] > h): continue
            if len(subq) and (subq["Close"] < lo).any():        continue
            return {"high": h, "low": lo, "mid": (h + lo) / 2,
                    "body_pct": body_pct, "bar_index": i}
        else:
            if cl <= o:                                          continue
            if not (nxt["Low"].min() < lo and nxt["Close"].iloc[-1] < lo): continue
            if len(subq) and (subq["Close"] > h).any():         continue
            return {"high": h, "low": lo, "mid": (h + lo) / 2,
                    "body_pct": body_pct, "bar_index": i}
    return None


# ─────────────────────────────────────────────
#  SMT Divergence
# ─────────────────────────────────────────────

def check_smt(direction: str, df_a: pd.DataFrame, df_b: pd.DataFrame) -> bool:
    w = 5
    if len(df_a) < w * 2 or len(df_b) < w * 2:
        return False
    if direction == "bullish":
        la = df_a["Low"].iloc[-w:].min();    lb = df_b["Low"].iloc[-w:].min()
        pa = df_a["Low"].iloc[-w*2:-w].min(); pb = df_b["Low"].iloc[-w*2:-w].min()
        return (la > pa) != (lb > pb)
    else:
        ha = df_a["High"].iloc[-w:].max();    hb = df_b["High"].iloc[-w:].max()
        pa = df_a["High"].iloc[-w*2:-w].max(); pb = df_b["High"].iloc[-w*2:-w].max()
        return (ha < pa) != (hb < pb)


# ─────────────────────────────────────────────
#  Confluence score
# ─────────────────────────────────────────────

def score_confluence(direction: str, htf: str, pdz: str,
                     smt_div: bool, body_pct: float, prox: float) -> tuple[int, list[str]]:
    score = 0
    details = []

    # 1. HTF aligned
    if (direction == "bullish" and htf == "BULLISH") or \
       (direction == "bearish" and htf == "BEARISH"):
        score += 1; details.append("✅ HTF aligned")
    else:
        details.append(f"❌ HTF misaligned ({htf})")

    # 2. PD Zone
    if (direction == "bullish" and pdz == "DISCOUNT") or \
       (direction == "bearish" and pdz == "PREMIUM"):
        score += 1; details.append(f"✅ {pdz} zone")
    else:
        details.append(f"⚠️ {pdz} zone (suboptimal)")

    # 3. SMT confirmation (no divergence = confirmed)
    if not smt_div:
        score += 1; details.append("✅ SMT confirmed")
    else:
        details.append("⚠️ SMT divergence")

    # 4. Strong OB body
    if body_pct >= 0.0015:
        score += 1; details.append(f"✅ Strong OB ({body_pct*100:.2f}%)")
    else:
        details.append(f"⚠️ Weak OB ({body_pct*100:.2f}%)")

    # 5. Close proximity to OB mid
    if prox <= OB_PROXIMITY_PCT * 0.5:
        score += 1; details.append(f"✅ Deep in OB ({prox*100:.3f}%)")
    else:
        details.append(f"⚠️ OB proximity {prox*100:.3f}%")

    return score, details


# ─────────────────────────────────────────────
#  Main scanner
# ─────────────────────────────────────────────

def scan_all(data: dict) -> list[dict]:
    """
    Scan all symbols for valid signals.
    data = { "NAS100": {"daily": df, "intraday": df}, ... }
    Returns list of signal dicts.
    """
    now = datetime.now(timezone.utc)
    in_kz, session_name = in_kill_zone(now)

    if not in_kz:
        logger.info("Not in kill zone — skipping scan (UTC %s)", now.strftime("%H:%M"))
        return []

    logger.info("In %s kill zone — scanning %d symbols", session_name, len(data))
    signals = []

    for symbol, dfs in data.items():
        daily_df    = dfs["daily"]
        intraday_df = dfs["intraday"]

        if intraday_df is None or len(intraday_df) < OB_LOOKBACK + 10:
            continue

        price = intraday_df["Close"].iloc[-1]
        htf   = get_htf_bias(daily_df)
        pdz   = get_pd_zone(intraday_df, price)

        for direction in ("bullish", "bearish"):
            if direction == "bullish" and htf == "BEARISH": continue
            if direction == "bearish" and htf == "BULLISH": continue

            ob = find_order_block(intraday_df, direction)
            if not ob:
                continue

            prox = abs(price - ob["mid"]) / price
            if prox > OB_PROXIMITY_PCT:
                continue

            # Directional bounds check
            if direction == "bullish" and price < ob["low"] * 0.995:  continue
            if direction == "bearish" and price > ob["high"] * 1.005: continue

            # Hard PD zone filter — SMC rule: longs from DISCOUNT, shorts from PREMIUM only
            # EQUILIBRIUM is allowed for both directions
            if direction == "bearish" and pdz == "DISCOUNT":
                logger.debug("%s bearish skipped — price in DISCOUNT zone (SMC violation)", symbol)
                continue
            if direction == "bullish" and pdz == "PREMIUM":
                logger.debug("%s bullish skipped — price in PREMIUM zone (SMC violation)", symbol)
                continue

            # SMT check
            smt_div = False
            sa, sb = SMT_PAIR
            if symbol in (sa, sb) and sa in data and sb in data:
                smt_div = check_smt(
                    direction,
                    data[sa]["intraday"],
                    data[sb]["intraday"]
                )

            score, details = score_confluence(direction, htf, pdz, smt_div,
                                               ob["body_pct"], prox)
            if score < MIN_CONFLUENCE:
                logger.debug("%s %s: score %d < %d — skipped",
                             symbol, direction, score, MIN_CONFLUENCE)
                continue

            # Build signal
            if direction == "bullish":
                entry = ob["mid"]
                stop  = ob["low"]  * (1 - 0.0005)
                risk  = entry - stop
                target = entry + risk * 2
            else:
                entry  = ob["mid"]
                stop   = ob["high"] * (1 + 0.0005)
                risk   = stop - entry
                target = entry - risk * 2

            signal = {
                "symbol":    symbol,
                "direction": direction,
                "session":   session_name,
                "timestamp": now,
                "price":     price,
                "entry":     round(entry, 4),
                "stop":      round(stop, 4),
                "target":    round(target, 4),
                "risk_pts":  round(abs(entry - stop), 4),
                "rr":        2.0,
                "score":     score,
                "htf":       htf,
                "pd_zone":   pdz,
                "smt_div":   smt_div,
                "details":   details,
                "ob":        ob,
            }
            signals.append(signal)
            logger.info("SIGNAL: %s %s | score %d/5 | entry %.4f | sl %.4f | tp %.4f",
                        symbol, direction.upper(), score, entry, stop, target)

    return signals