"""
risk_manager.py — Enforces prop firm challenge rules for both accounts.
                  Calculates position size and blocks trades near limits.
"""

import logging
from config import ACCOUNTS, RR_RATIO

logger = logging.getLogger("eden.risk")


def get_account_state(account_id: str) -> dict:
    """Return a live-refreshable copy of account state (extend to pull from API later)."""
    return dict(ACCOUNTS[account_id])


def check_trade_allowed(account_id: str, proposed_risk_usd: float) -> tuple[bool, str]:
    """
    Returns (allowed: bool, reason: str).
    Blocks trade if it would breach max loss or daily loss.
    """
    acc = get_account_state(account_id)

    # ── Daily loss check ──────────────────────────────────
    if proposed_risk_usd > acc["daily_loss_target"] * 0.90:
        return False, (
            f"🚫 Daily loss guard: proposed risk ${proposed_risk_usd:.2f} "
            f"would use >{90}% of remaining daily limit "
            f"(${acc['daily_loss_target']:.2f} left)"
        )

    # ── Max loss check ────────────────────────────────────
    headroom = acc["equity"] - acc["max_loss_threshold"]
    if proposed_risk_usd > headroom * 0.80:
        return False, (
            f"🚫 Max loss guard: only ${headroom:.2f} headroom before breach. "
            f"Proposed risk ${proposed_risk_usd:.2f} too large."
        )

    # ── Already at profit target (funded account keep going) ──
    if acc["profit_target"] > 0:
        profit_left = acc["profit_target"] - acc["profit_achieved"]
        if profit_left <= 0:
            return True, "ℹ️ Profit target already hit — running conservatively"

    return True, "✅ Trade allowed"


def calculate_position_size(account_id: str, entry: float, stop: float) -> dict:
    """
    Returns dict with:
        units       — number of index units/contracts
        risk_usd    — dollar risk
        risk_pct    — as % of equity
        tp_price    — take profit price
        direction   — bullish/bearish
    """
    acc    = get_account_state(account_id)
    equity = acc["equity"]
    risk_frac = acc["risk_per_trade"]
    risk_usd  = equity * risk_frac

    direction = "bullish" if entry > stop else "bearish"
    distance  = abs(entry - stop)

    if distance == 0:
        return {"error": "Stop == entry — invalid signal"}

    units = risk_usd / distance

    tp = (entry + distance * RR_RATIO) if direction == "bullish" \
         else (entry - distance * RR_RATIO)

    return {
        "account_id":  account_id,
        "account_name": acc["name"],
        "direction":   direction,
        "equity":      equity,
        "risk_usd":    round(risk_usd, 2),
        "risk_pct":    round(risk_frac * 100, 1),
        "units":       round(units, 4),
        "entry":       round(entry, 4),
        "stop":        round(stop, 4),
        "tp":          round(tp, 4),
        "rr":          RR_RATIO,
        "daily_remaining": acc["daily_loss_target"],
        "max_headroom":    round(acc["equity"] - acc["max_loss_threshold"], 2),
    }


def build_trade_plan(signal: dict) -> list[dict]:
    """
    Generate a trade plan for ALL accounts for a given signal.
    Returns list of trade plan dicts, one per account that passes risk checks.
    """
    plans = []
    for acc_id in ACCOUNTS:
        sizing = calculate_position_size(acc_id, signal["entry"], signal["stop"])
        if "error" in sizing:
            logger.warning("Sizing error for %s: %s", acc_id, sizing["error"])
            continue

        allowed, reason = check_trade_allowed(acc_id, sizing["risk_usd"])
        sizing["allowed"] = allowed
        sizing["reason"]  = reason
        plans.append(sizing)

        if not allowed:
            logger.warning("Trade BLOCKED for account %s: %s", acc_id, reason)
        else:
            logger.info("Trade approved for account %s: risk $%.2f (%.1f%%)",
                        acc_id, sizing["risk_usd"], sizing["risk_pct"])
    return plans


def account_summary(account_id: str) -> dict:
    """Return a risk summary suitable for Telegram / Google Sheets."""
    acc = get_account_state(account_id)
    profit_pct = (acc["profit_achieved"] / acc["profit_target"] * 100) \
                 if acc["profit_target"] > 0 else 100.0
    loss_used  = acc["max_loss_target"] - acc["max_loss_remaining"]
    loss_pct   = (loss_used / acc["max_loss_target"] * 100) if acc["max_loss_target"] else 0

    return {
        "account_id":    account_id,
        "name":          acc["name"],
        "equity":        acc["equity"],
        "balance":       acc["balance"],
        "profit_achieved": acc["profit_achieved"],
        "profit_target":   acc["profit_target"],
        "profit_pct":      round(profit_pct, 1),
        "max_loss_remaining": acc["max_loss_remaining"],
        "max_loss_used_pct":  round(loss_pct, 1),
        "daily_remaining":    acc["daily_loss_target"],
        "daily_target":       acc["daily_loss_target"],
        "max_loss_threshold": acc["max_loss_threshold"],
        "status": "🟢 HEALTHY" if loss_pct < 60 else
                  "🟡 CAUTION" if loss_pct < 85 else "🔴 DANGER",
    }