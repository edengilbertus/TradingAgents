"""
notifier.py — Telegram message formatter and sender.
              Enhanced with AI daily bias + alignment tags.
"""

import logging
import requests
from datetime import datetime, timezone, timedelta
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, ACCOUNTS

logger = logging.getLogger("eden.notifier")

TG_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

PAYOUT_DATES = {
    "502208": "2026-03-27",
}


def _send(text: str, parse_mode: str = "HTML") -> bool:
    try:
        r = requests.post(TG_URL, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }, timeout=10)
        r.raise_for_status()
        return True
    except Exception as e:
        logger.error("Telegram send failed: %s", e)
        return False


# ─────────────────────────────────────────────
#  AI Daily Bias (NEW)
# ─────────────────────────────────────────────

_AI_ARROWS = {
    "Buy": "▲", "Overweight": "▲",
    "Hold": "●",
    "Underweight": "▼", "Sell": "▼",
    "ERROR": "⚠️",
}


def send_ai_daily_bias(biases: dict, position_changes: list) -> None:
    """Send the daily AI bias message to Telegram."""
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%a %d %b %Y")

    lines = [
        f"🧠 <b>AI DAILY BIAS — {date_str}</b>",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
    ]

    for symbol, bias in biases.items():
        rating = bias.get("rating", "ERROR")
        arrow = _AI_ARROWS.get(rating, "?")
        lines.append(f"📊 <b>{symbol}</b>    {rating.upper()} {arrow}")

        # Find position change info for this symbol
        change = next(
            (c for c in position_changes if c["symbol"] == symbol),
            None,
        )

        if change and change["changed"]:
            lines.append(
                f"   ⚠️ BIAS CHANGED: {change['previous_rating']} → {rating}"
            )
            if change["days_in_position"] > 0:
                direction_str = change.get("position_direction") or "position"
                lines.append(
                    f"   Day {change['days_in_position']} of "
                    f"{direction_str} — review stop"
                )
        elif change and change["days_in_position"] > 0:
            lines.append(
                f"   ✅ Bias unchanged — Day {change['days_in_position']}"
            )

        summary = bias.get("summary", "")
        if summary and rating != "ERROR":
            lines.append(f"   <i>{summary[:120]}</i>")

        lines.append("")

    lines.extend([
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "<i>4 analysts → bull/bear debate → risk review</i>",
    ])

    _send("\n".join(lines))


def get_ai_alignment_tag(ai_biases: dict, symbol: str, direction: str) -> str | None:
    """Check if an SMC signal aligns with the AI daily bias.

    Args:
        ai_biases: Current daily biases dict from get_daily_biases()
        symbol: e.g. "NAS100"
        direction: "bullish" or "bearish" (matches scanner.py output)

    Returns:
        Alignment string to append to signal message, or None
    """
    if not ai_biases:
        return None

    bias = ai_biases.get(symbol, {})
    rating = bias.get("rating", "").strip()
    if not rating or rating == "ERROR":
        return None

    rating_lower = rating.lower()
    bullish_ratings = {"buy", "overweight"}
    bearish_ratings = {"sell", "underweight"}

    if direction == "bullish" and rating_lower in bullish_ratings:
        return f"✅ <b>ALIGNS</b> with AI daily bias ({rating.upper()})"
    elif direction == "bearish" and rating_lower in bearish_ratings:
        return f"✅ <b>ALIGNS</b> with AI daily bias ({rating.upper()})"
    elif rating_lower == "hold":
        return f"⚪ AI daily bias is <b>HOLD</b> — proceed with caution"
    elif direction == "bullish" and rating_lower in bearish_ratings:
        return f"⚠️ <b>AGAINST</b> AI daily bias ({rating.upper()})"
    elif direction == "bearish" and rating_lower in bullish_ratings:
        return f"⚠️ <b>AGAINST</b> AI daily bias ({rating.upper()})"
    return None


# ─────────────────────────────────────────────
#  Signal alert (MODIFIED — added ai_alignment param)
# ─────────────────────────────────────────────

def send_signal(signal: dict, plans: list[dict],
                ai_alignment: str | None = None) -> None:
    d = signal
    arrow = "📈" if d["direction"] == "bullish" else "📉"
    emoji = "🟢" if d["direction"] == "bullish" else "🔴"
    now   = d["timestamp"].strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        f"{arrow} <b>EDEN SMC SIGNAL</b> {arrow}",
        f"",
        f"{emoji} <b>{d['symbol']}</b> — {d['direction'].upper()}",
        f"🕐 <b>Session:</b> {d['session']} | {now}",
        f"",
        f"📊 <b>Entry:</b>  <code>{d['entry']:.4f}</code>",
        f"🛑 <b>Stop:</b>   <code>{d['stop']:.4f}</code>",
        f"🎯 <b>Target:</b> <code>{d['target']:.4f}</code>",
        f"",
        f"⚡ <b>RR:</b> 1:{d['rr']}  |  <b>Score:</b> {d['score']}/5",
        f"📍 <b>HTF Bias:</b> {d['htf']}  |  <b>Zone:</b> {d['pd_zone']}",
        f"",
        f"<b>Confluence:</b>",
    ]
    for detail in d["details"]:
        lines.append(f"  {detail}")

    # ── AI alignment tag (NEW) ──
    if ai_alignment:
        lines += ["", "─────────────────────", ai_alignment]

    lines += ["", "─────────────────────", "<b>Position Sizing:</b>"]
    for plan in plans:
        if plan["allowed"]:
            lines.append(
                f"  🏦 <b>{plan['account_name']}</b> ({plan['account_id']})\n"
                f"     Units: <code>{plan['units']:.4f}</code>  "
                f"Risk: ${plan['risk_usd']:.2f} ({plan['risk_pct']}%)\n"
                f"     Daily left: ${plan['daily_remaining']:.2f}  "
                f"Headroom: ${plan['max_headroom']:.2f}"
            )
        else:
            lines.append(
                f"  ⛔ <b>{plan['account_name']}</b>: {plan['reason']}"
            )

    lines.append("\n<i>This is an automated signal. Always verify manually.</i>")
    _send("\n".join(lines))


# ─────────────────────────────────────────────
#  Hourly update
# ─────────────────────────────────────────────

def send_hourly_update(summaries: list[dict], signals_today: int,
                       last_signal: dict | None = None) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"🕐 <b>EDEN BOT — HOURLY UPDATE</b>",
        f"<i>{now}</i>",
        f"",
        f"📡 <b>Signals fired today:</b> {signals_today}",
    ]
    if last_signal:
        lines.append(
            f"📌 <b>Last signal:</b> {last_signal['symbol']} "
            f"{last_signal['direction'].upper()} @ {last_signal['entry']:.4f}"
        )
    lines += ["", "─────────────────────", "<b>Account Health:</b>"]

    for s in summaries:
        acc_id  = s["account_id"]
        is_funded = s["profit_target"] == 0

        loss_bar = _progress_bar(s["max_loss_used_pct"], 100, invert=True)

        lines += ["", f"🏦 <b>{s['name']}</b> ({acc_id}) {s['status']}"]
        lines.append(f"  💰 Equity: <b>${s['equity']:,.2f}</b>")

        if is_funded:
            # Funded account — show payout countdown instead of profit bar
            payout_str = ""
            if acc_id in PAYOUT_DATES:
                try:
                    payout_dt = datetime.strptime(PAYOUT_DATES[acc_id], "%Y-%m-%d")\
                                        .replace(tzinfo=timezone.utc)
                    days_left = (payout_dt - datetime.now(timezone.utc)).days
                    if days_left >= 0:
                        payout_str = f" · 💸 Payout in <b>{days_left}d</b> ({PAYOUT_DATES[acc_id]})"
                    else:
                        payout_str = f" · 💸 Payout due ({PAYOUT_DATES[acc_id]})"
                except Exception:
                    pass
            lines.append(f"  ✅ Funded account — payout mode{payout_str}")
            lines.append(f"  📈 Profit so far: ${s['profit_achieved']:,.2f}")
        else:
            profit_bar = _progress_bar(s["profit_pct"], 100)
            lines.append(f"  📈 Profit: ${s['profit_achieved']:,.2f} / ${s['profit_target']:,.2f}")
            lines.append(f"     {profit_bar} {s['profit_pct']:.1f}%")

        lines.append(f"  📉 Max Loss Used: {s['max_loss_used_pct']:.1f}%")
        lines.append(f"     {loss_bar}")
        lines.append(f"  🛡 Daily limit left: ${s['daily_remaining']:.2f}")
        lines.append(f"  ⚠️ Breach threshold: ${s['max_loss_threshold']:,.2f}")

    lines.append("\n<i>Next update in 1 hour</i>")
    _send("\n".join(lines))


# ─────────────────────────────────────────────
#  Breach warning (fires immediately, not hourly)
# ─────────────────────────────────────────────

BREACH_WARNING_THRESHOLD = {
    "139625": 50.0,  # warn when max loss remaining drops below $50
    "502208": 30.0,
}
_breach_warned: set[str] = set()


def check_and_send_breach_warning(summaries: list[dict]) -> None:
    """Call this after every scan. Fires a one-time Telegram alert if headroom is critical."""
    for s in summaries:
        acc_id    = s["account_id"]
        remaining = s["max_loss_remaining"]
        threshold = BREACH_WARNING_THRESHOLD.get(acc_id, 50.0)

        if remaining <= threshold and acc_id not in _breach_warned:
            _breach_warned.add(acc_id)
            _send(
                f"🚨 <b>BREACH WARNING — {s['name']}</b> ({acc_id})\n"
                f"\n"
                f"Max loss remaining: <b>${remaining:.2f}</b>\n"
                f"Breach threshold:   ${s['max_loss_threshold']:,.2f}\n"
                f"\n"
                f"⛔ The bot will block new trades until headroom recovers.\n"
                f"<i>Review your open positions immediately.</i>"
            )
            logger.warning("BREACH WARNING sent for account %s (remaining: $%.2f)", acc_id, remaining)
        elif remaining > threshold and acc_id in _breach_warned:
            _breach_warned.discard(acc_id)  # reset if headroom recovers


def _progress_bar(pct: float, total: float = 100, invert: bool = False,
                  length: int = 10) -> str:
    filled = min(int(pct / total * length), length)
    bar = "█" * filled + "░" * (length - filled)
    return f"[{bar}]"


# ─────────────────────────────────────────────
#  Bot status messages (MODIFIED — mentions AI bias)
# ─────────────────────────────────────────────

def send_startup() -> None:
    _send(
        "🚀 <b>Eden SMC Bot — STARTED</b>\n"
        "Scanning NAS100 · US30 · US500\n"
        "Sessions: London 07–10 UTC | NY 12–15 UTC\n"
        "Kill zones: Tue · Wed · Thu\n"
        "Data: Twelve Data (15-min) + Yahoo Finance (HTF)\n"
        "🧠 AI Bias: Gemini 2.5 · runs daily at 06:30 UTC\n"
        "Signals → Telegram  |  Log → Google Sheets\n"
        "<i>Bot is live and scanning...</i>"
    )


def send_error(context: str, error: str) -> None:
    _send(f"⚠️ <b>Eden Bot ERROR</b>\n<code>{context}</code>\n{error}")


def send_no_signal_in_session(session: str, symbols_scanned: int) -> None:
    _send(
        f"🔍 <b>{session} session scan complete</b>\n"
        f"Scanned {symbols_scanned} symbols — no qualifying signals this session.\n"
        f"<i>Next scan at next kill zone.</i>"
    )
