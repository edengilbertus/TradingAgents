"""
AI Bias module — runs TradingAgents multi-agent analysis for each index
and returns a directional bias (Buy/Overweight/Hold/Underweight/Sell)
with a one-line summary.

Designed to run once daily before London kill zone (~06:30 UTC).
Each index takes ~1-2 minutes, so 3 indices ≈ 5 minutes total.

Usage:
    biases = get_daily_biases()
    # Returns: {
    #   "NAS100": {"rating": "Buy", "summary": "Strong tech momentum..."},
    #   "US30":   {"rating": "Hold", "summary": "Mixed signals..."},
    #   "US500":  {"rating": "Sell", "summary": "Bearish divergence..."},
    # }
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from config import (
    SYMBOLS,
    GOOGLE_API_KEY,
    AI_LLM_PROVIDER,
    AI_DEEP_MODEL,
    AI_QUICK_MODEL,
    AI_BIAS_ENABLED,
)

logger = logging.getLogger("eden.ai_bias")


def get_daily_biases() -> dict:
    """Run TradingAgents for each symbol and return bias dict.

    Heavy imports are delayed so the eden_bot starts fast; the
    TradingAgents graph is only loaded when this function is called.
    """
    if not AI_BIAS_ENABLED:
        logger.info("AI bias disabled in config — skipping")
        return {}

    # Set API key before importing TradingAgents internals
    os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

    from tradingagents.graph.trading_graph import TradingAgentsGraph
    from tradingagents.default_config import DEFAULT_CONFIG

    config = DEFAULT_CONFIG.copy()
    config["llm_provider"] = AI_LLM_PROVIDER
    config["deep_think_llm"] = AI_DEEP_MODEL
    config["quick_think_llm"] = AI_QUICK_MODEL
    config["max_debate_rounds"] = 1
    config["max_risk_discuss_rounds"] = 1
    config["data_vendors"] = {
        "core_stock_apis": "yfinance",
        "technical_indicators": "yfinance",
        "fundamental_data": "yfinance",
        "news_data": "yfinance",
    }

    graph = TradingAgentsGraph(debug=False, config=config)
    today = datetime.now(timezone.utc).date().isoformat()

    biases: dict = {}
    for symbol in SYMBOLS:
        logger.info("Running AI analysis for %s ...", symbol)
        try:
            state, decision = graph.propagate(symbol, today)
            summary = _extract_summary(state)
            biases[symbol] = {
                "rating": decision,
                "summary": summary,
                "market_report": state.get("market_report", ""),
                "fundamentals_report": state.get("fundamentals_report", ""),
            }
            logger.info("AI bias for %s: %s", symbol, decision)
        except Exception as e:
            logger.exception("AI bias failed for %s: %s", symbol, e)
            biases[symbol] = {
                "rating": "ERROR",
                "summary": str(e)[:150],
            }

    return biases


def _extract_summary(state: dict) -> str:
    """Pull a one-line summary from the final trade decision."""
    decision_text = state.get("final_trade_decision", "")
    # Look for the Executive Summary line from structured output
    for line in decision_text.split("\n"):
        if "Executive Summary" in line:
            clean = line.replace("**Executive Summary**:", "").replace("**Executive Summary**", "").strip()
            if clean:
                return clean[:200]
    # Fallback: first meaningful line
    for line in decision_text.split("\n"):
        stripped = line.strip()
        if stripped and not stripped.startswith("**") and len(stripped) > 20:
            return stripped[:200]
    return decision_text[:150].strip() if decision_text else "No summary available"
