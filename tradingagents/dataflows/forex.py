"""Utilities for recognizing and describing forex instruments.

TradingAgents originally treated every instrument as an equity ticker.  Forex
pairs need a small amount of shared normalization so CLI input, data vendors,
cache paths, and agent prompts all refer to the same instrument.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Optional


# Broad ISO-4217 currency-code allowlist.  This keeps six-letter equity symbols
# from being accidentally treated as FX while covering common tradable pairs.
KNOWN_CURRENCY_CODES = {
    "AED", "AFN", "ALL", "AMD", "ANG", "AOA", "ARS", "AUD", "AWG", "AZN",
    "BAM", "BBD", "BDT", "BGN", "BHD", "BIF", "BMD", "BND", "BOB", "BRL",
    "BSD", "BTN", "BWP", "BYN", "BZD", "CAD", "CDF", "CHF", "CLP", "CNH",
    "CNY", "COP", "CRC", "CUP", "CVE", "CZK", "DJF", "DKK", "DOP", "DZD",
    "EGP", "ERN", "ETB", "EUR", "FJD", "FKP", "GBP", "GEL", "GHS", "GIP",
    "GMD", "GNF", "GTQ", "GYD", "HKD", "HNL", "HRK", "HTG", "HUF", "IDR",
    "ILS", "INR", "IQD", "IRR", "ISK", "JMD", "JOD", "JPY", "KES", "KGS",
    "KHR", "KMF", "KRW", "KWD", "KYD", "KZT", "LAK", "LBP", "LKR", "LRD",
    "LSL", "LYD", "MAD", "MDL", "MGA", "MKD", "MMK", "MNT", "MOP", "MRU",
    "MUR", "MVR", "MWK", "MXN", "MYR", "MZN", "NAD", "NGN", "NIO", "NOK",
    "NPR", "NZD", "OMR", "PAB", "PEN", "PGK", "PHP", "PKR", "PLN", "PYG",
    "QAR", "RON", "RSD", "RUB", "RWF", "SAR", "SBD", "SCR", "SDG", "SEK",
    "SGD", "SHP", "SLE", "SOS", "SRD", "SSP", "STN", "SYP", "SZL", "THB",
    "TJS", "TMT", "TND", "TOP", "TRY", "TTD", "TWD", "TZS", "UAH", "UGX",
    "USD", "UYU", "UZS", "VES", "VND", "VUV", "WST", "XAF", "XCD", "XOF",
    "XPF", "YER", "ZAR", "ZMW", "ZWL",
}


_FOREX_PAIR_RE = re.compile(r"^([A-Z]{3})[/_\-]?([A-Z]{3})(?:=X)?$")


@dataclass(frozen=True)
class ForexPair:
    base: str
    quote: str

    @property
    def yfinance_symbol(self) -> str:
        return f"{self.base}{self.quote}=X"

    @property
    def alpha_vantage_symbol(self) -> str:
        return f"{self.base}{self.quote}"

    @property
    def display_symbol(self) -> str:
        return f"{self.base}/{self.quote}"


def parse_forex_pair(symbol: str) -> Optional[ForexPair]:
    """Return a ForexPair for supported FX symbols, otherwise None.

    Accepted examples: ``EURUSD=X``, ``EURUSD``, ``EUR/USD``, ``EUR-USD``.
    """
    if not isinstance(symbol, str):
        return None

    normalized = symbol.strip().upper().replace(" ", "")
    match = _FOREX_PAIR_RE.fullmatch(normalized)
    if not match:
        return None

    base, quote = match.groups()
    if base == quote:
        return None
    if base not in KNOWN_CURRENCY_CODES or quote not in KNOWN_CURRENCY_CODES:
        return None
    return ForexPair(base=base, quote=quote)


def is_forex_pair(symbol: str) -> bool:
    return parse_forex_pair(symbol) is not None


def normalize_forex_symbol(symbol: str) -> Optional[str]:
    pair = parse_forex_pair(symbol)
    return pair.yfinance_symbol if pair else None


def forex_context(symbol: str) -> str:
    """Return prompt context for an FX pair, or an empty string for non-FX."""
    pair = parse_forex_pair(symbol)
    if not pair:
        return ""

    return (
        f"The instrument is a forex pair: {pair.display_symbol} "
        f"({pair.yfinance_symbol}). Base currency: {pair.base}. "
        f"Quote currency: {pair.quote}. Interpret Buy/Overweight as long "
        f"{pair.base} / short {pair.quote}; interpret Sell/Underweight as short "
        f"{pair.base} / long {pair.quote}; Hold means no new directional exposure. "
        "Treat fundamentals as macro fundamentals: central-bank policy, rates, "
        "inflation, labor data, growth, fiscal policy, trade balances, commodity "
        "exposure, geopolitical risk, and cross-asset risk sentiment. Do not use "
        "equity-only concepts such as market cap, earnings, dividends, balance "
        "sheets, insider transactions, or company management quality unless a "
        "source explicitly connects them to the currency pair."
    )


def forex_macro_fundamentals(symbol: str, curr_date: str = None) -> str:
    """Return an FX-specific fundamental-analysis scaffold for an FX pair."""
    pair = parse_forex_pair(symbol)
    if not pair:
        raise ValueError(f"not a recognized forex pair: {symbol}")

    date_line = f" as of {curr_date}" if curr_date else ""
    return (
        f"# Forex Macro Fundamentals for {pair.display_symbol}{date_line}\n\n"
        f"This is a currency pair, not an equity. Analyze {pair.base} versus "
        f"{pair.quote} through relative macro fundamentals:\n"
        "- Central-bank policy stance, expected rate path, real yield direction, "
        "and policy divergence.\n"
        "- Inflation trend, labor-market momentum, GDP/growth surprises, and "
        "fiscal impulse in both economies.\n"
        "- Current-account/trade balance, commodity exposure, reserve status, "
        "safe-haven demand, and external funding risks.\n"
        "- Market positioning, volatility regime, carry, liquidity, and broad "
        "risk appetite.\n"
        f"Directional convention: Buy means long {pair.base} / short {pair.quote}; "
        f"Sell means short {pair.base} / long {pair.quote}."
    )


def forex_not_applicable(symbol: str, data_name: str) -> str:
    pair = parse_forex_pair(symbol)
    display = pair.display_symbol if pair else symbol
    return (
        f"{data_name} is not applicable to forex pair {display}. Use macro "
        "fundamentals, central-bank policy, rates, inflation, growth, trade "
        "balances, positioning, and risk sentiment instead."
    )
