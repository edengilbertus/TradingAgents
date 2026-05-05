"""
Track open positions and detect AI bias changes for monthly holds.
Persists to data/positions.json so it survives bot restarts.

Usage:
    from position_tracker import update_bias, mark_position_open, mark_position_closed

    # Called automatically by the daily AI bias job:
    change = update_bias("NAS100", "Buy")
    # Returns: {"symbol": "NAS100", "previous_rating": "Hold", "new_rating": "Buy",
    #           "changed": True, "days_in_position": 15, "position_direction": "long"}

    # Called manually (future Telegram command integration):
    mark_position_open("NAS100", "long")
    mark_position_closed("NAS100")
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

POSITIONS_FILE = os.path.join(os.path.dirname(__file__), "data", "positions.json")
logger = logging.getLogger("eden.positions")


def load_positions() -> dict:
    """Load positions from JSON file."""
    if os.path.exists(POSITIONS_FILE):
        try:
            with open(POSITIONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Could not load positions file: %s", e)
    return {}


def save_positions(positions: dict) -> None:
    """Persist positions to JSON file."""
    os.makedirs(os.path.dirname(POSITIONS_FILE), exist_ok=True)
    with open(POSITIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(positions, f, indent=2)


def update_bias(symbol: str, new_rating: str) -> dict:
    """Update the stored bias for a symbol and detect changes.

    Returns:
        dict with keys: symbol, previous_rating, new_rating, changed,
        days_in_position, position_direction
    """
    positions = load_positions()
    prev = positions.get(symbol, {})
    prev_rating = prev.get("current_rating")

    changed = prev_rating is not None and prev_rating != new_rating

    # Track position duration
    position_info = prev.get("position", {})
    days = 0
    if position_info.get("entry_date"):
        try:
            entry = datetime.fromisoformat(position_info["entry_date"])
            days = (datetime.now(timezone.utc) - entry).days
        except (ValueError, TypeError):
            days = 0

    # Update stored state
    positions[symbol] = {
        "current_rating": new_rating,
        "previous_rating": prev_rating,
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "rating_history": prev.get("rating_history", []) + [{
            "rating": new_rating,
            "date": datetime.now(timezone.utc).date().isoformat(),
        }],
        "position": position_info,
    }

    # Keep only last 30 days of rating history
    positions[symbol]["rating_history"] = positions[symbol]["rating_history"][-30:]

    save_positions(positions)

    return {
        "symbol": symbol,
        "previous_rating": prev_rating,
        "new_rating": new_rating,
        "changed": changed,
        "days_in_position": days,
        "position_direction": position_info.get("direction"),
    }


def mark_position_open(symbol: str, direction: str) -> None:
    """Mark a position as opened."""
    positions = load_positions()
    if symbol not in positions:
        positions[symbol] = {"current_rating": None, "previous_rating": None}
    positions[symbol]["position"] = {
        "direction": direction,
        "entry_date": datetime.now(timezone.utc).isoformat(),
    }
    save_positions(positions)
    logger.info("Position opened: %s %s", symbol, direction)


def mark_position_closed(symbol: str) -> None:
    """Mark a position as closed."""
    positions = load_positions()
    if symbol in positions:
        positions[symbol]["position"] = {}
    save_positions(positions)
    logger.info("Position closed: %s", symbol)


def get_all_positions() -> dict:
    """Return all tracked positions for display."""
    return load_positions()
