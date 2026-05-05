"""Utilities for recognizing and describing market index instruments.

TradingAgents originally treated every instrument as an equity ticker.  Forex
pairs received their own detection layer.  This module adds the same kind of
normalization for market indices so CLI input, data vendors, cache paths, and
agent prompts all refer to the same instrument.

Supports common index aliases used by brokers and trading platforms (e.g.
US30, US100, US500, NAS100) alongside canonical Yahoo Finance symbols
(^DJI, ^NDX, ^GSPC).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class IndexInfo:
    """Describes a market index instrument."""

    symbol: str          # Canonical short name (e.g. "US30")
    name: str            # Human-readable full name
    yfinance_symbol: str  # Yahoo Finance ticker (e.g. "^DJI")
    benchmark_etf: str    # Most liquid ETF proxy (e.g. "DIA")
    components_desc: str  # Brief description of what the index tracks


# ── Known indices ──────────────────────────────────────────────────────────
# Maps uppercase aliases → IndexInfo.  Multiple aliases may point to the same
# index so users can type whatever their broker calls it.

_US30 = IndexInfo(
    symbol="US30",
    name="Dow Jones Industrial Average",
    yfinance_symbol="^DJI",
    benchmark_etf="DIA",
    components_desc="30 large-cap US blue-chip stocks",
)

_US100 = IndexInfo(
    symbol="US100",
    name="NASDAQ-100",
    yfinance_symbol="^NDX",
    benchmark_etf="QQQ",
    components_desc="100 largest non-financial NASDAQ-listed companies",
)

_US500 = IndexInfo(
    symbol="US500",
    name="S&P 500",
    yfinance_symbol="^GSPC",
    benchmark_etf="SPY",
    components_desc="500 large-cap US companies",
)

_NASDAQ_COMPOSITE = IndexInfo(
    symbol="NASDAQ",
    name="NASDAQ Composite",
    yfinance_symbol="^IXIC",
    benchmark_etf="QQQ",
    components_desc="All NASDAQ-listed stocks (3,000+)",
)

_RUSSELL2000 = IndexInfo(
    symbol="RUSSELL2000",
    name="Russell 2000",
    yfinance_symbol="^RUT",
    benchmark_etf="IWM",
    components_desc="2,000 small-cap US stocks",
)

_VIX = IndexInfo(
    symbol="VIX",
    name="CBOE Volatility Index",
    yfinance_symbol="^VIX",
    benchmark_etf="VIXY",
    components_desc="S&P 500 implied volatility (the 'fear gauge')",
)

_DAX = IndexInfo(
    symbol="DAX",
    name="DAX 40",
    yfinance_symbol="^GDAXI",
    benchmark_etf="EWG",
    components_desc="40 largest German blue-chip stocks",
)

_FTSE = IndexInfo(
    symbol="FTSE",
    name="FTSE 100",
    yfinance_symbol="^FTSE",
    benchmark_etf="EWU",
    components_desc="100 largest UK-listed companies",
)

_CAC40 = IndexInfo(
    symbol="CAC40",
    name="CAC 40",
    yfinance_symbol="^FCHI",
    benchmark_etf="EWQ",
    components_desc="40 largest French stocks",
)

_NIKKEI = IndexInfo(
    symbol="NIKKEI",
    name="Nikkei 225",
    yfinance_symbol="^N225",
    benchmark_etf="EWJ",
    components_desc="225 largest Japanese stocks",
)

_HANGSENG = IndexInfo(
    symbol="HSI",
    name="Hang Seng Index",
    yfinance_symbol="^HSI",
    benchmark_etf="EWH",
    components_desc="~80 largest Hong Kong-listed companies",
)

_SSE = IndexInfo(
    symbol="SSE",
    name="Shanghai Composite",
    yfinance_symbol="000001.SS",
    benchmark_etf="FXI",
    components_desc="All stocks on the Shanghai Stock Exchange",
)

_STOXX50 = IndexInfo(
    symbol="STOXX50",
    name="Euro Stoxx 50",
    yfinance_symbol="^STOXX50E",
    benchmark_etf="FEZ",
    components_desc="50 largest Eurozone blue-chip stocks",
)

_ASX200 = IndexInfo(
    symbol="ASX200",
    name="S&P/ASX 200",
    yfinance_symbol="^AXJO",
    benchmark_etf="EWA",
    components_desc="200 largest Australian stocks",
)

_KOSPI = IndexInfo(
    symbol="KOSPI",
    name="KOSPI Composite",
    yfinance_symbol="^KS11",
    benchmark_etf="EWY",
    components_desc="All common stocks on the Korea Exchange",
)

_SENSEX = IndexInfo(
    symbol="SENSEX",
    name="BSE Sensex",
    yfinance_symbol="^BSESN",
    benchmark_etf="INDA",
    components_desc="30 largest Indian stocks on BSE",
)

_NIFTY50 = IndexInfo(
    symbol="NIFTY50",
    name="Nifty 50",
    yfinance_symbol="^NSEI",
    benchmark_etf="INDA",
    components_desc="50 largest Indian stocks on NSE",
)

_TSX = IndexInfo(
    symbol="TSX",
    name="S&P/TSX Composite",
    yfinance_symbol="^GSPTSE",
    benchmark_etf="EWC",
    components_desc="~250 largest Canadian stocks",
)

_IBOVESPA = IndexInfo(
    symbol="IBOVESPA",
    name="Bovespa",
    yfinance_symbol="^BVSP",
    benchmark_etf="EWZ",
    components_desc="~85 largest Brazilian stocks",
)

# Alias mapping — case insensitive lookup (keys are uppercase)
KNOWN_INDICES: dict[str, IndexInfo] = {
    # US indices
    "US30": _US30,
    "DJ30": _US30,
    "DJIA": _US30,
    "DOW": _US30,
    "DOWJONES": _US30,
    "^DJI": _US30,

    "US100": _US100,
    "NAS100": _US100,
    "NASDAQ100": _US100,
    "NDX": _US100,
    "^NDX": _US100,

    "US500": _US500,
    "SPX": _US500,
    "SP500": _US500,
    "SPX500": _US500,
    "^GSPC": _US500,

    "NASDAQ": _NASDAQ_COMPOSITE,
    "NASDAQCOMP": _NASDAQ_COMPOSITE,
    "^IXIC": _NASDAQ_COMPOSITE,

    "RUSSELL2000": _RUSSELL2000,
    "RUT": _RUSSELL2000,
    "US2000": _RUSSELL2000,
    "^RUT": _RUSSELL2000,

    "VIX": _VIX,
    "^VIX": _VIX,

    # European indices
    "DAX": _DAX,
    "DAX40": _DAX,
    "GER40": _DAX,
    "DE40": _DAX,
    "^GDAXI": _DAX,

    "FTSE": _FTSE,
    "FTSE100": _FTSE,
    "UK100": _FTSE,
    "^FTSE": _FTSE,

    "CAC40": _CAC40,
    "FRA40": _CAC40,
    "FR40": _CAC40,
    "^FCHI": _CAC40,

    "STOXX50": _STOXX50,
    "EU50": _STOXX50,
    "EUROSTOXX50": _STOXX50,
    "^STOXX50E": _STOXX50,

    # Asian indices
    "NIKKEI": _NIKKEI,
    "NIKKEI225": _NIKKEI,
    "JP225": _NIKKEI,
    "JPN225": _NIKKEI,
    "^N225": _NIKKEI,

    "HSI": _HANGSENG,
    "HANGSENG": _HANGSENG,
    "HK50": _HANGSENG,
    "^HSI": _HANGSENG,

    "SSE": _SSE,
    "SHANGHAI": _SSE,
    "000001.SS": _SSE,

    "KOSPI": _KOSPI,
    "^KS11": _KOSPI,

    "SENSEX": _SENSEX,
    "^BSESN": _SENSEX,

    "NIFTY50": _NIFTY50,
    "NIFTY": _NIFTY50,
    "^NSEI": _NIFTY50,

    # Oceania
    "ASX200": _ASX200,
    "AUS200": _ASX200,
    "^AXJO": _ASX200,

    # Americas (ex-US)
    "TSX": _TSX,
    "^GSPTSE": _TSX,

    "IBOVESPA": _IBOVESPA,
    "BVSP": _IBOVESPA,
    "^BVSP": _IBOVESPA,
}


def parse_index(symbol: str) -> Optional[IndexInfo]:
    """Return an IndexInfo for recognized index symbols, otherwise None.

    Accepted examples: ``US30``, ``^DJI``, ``NASDAQ100``, ``NAS100``,
    ``SP500``, ``DAX``, ``NIKKEI``, ``UK100``, etc.
    """
    if not isinstance(symbol, str):
        return None
    normalized = symbol.strip().upper().replace(" ", "")
    return KNOWN_INDICES.get(normalized)


def is_index(symbol: str) -> bool:
    """Return True if symbol is a recognized market index."""
    return parse_index(symbol) is not None


def normalize_index_symbol(symbol: str) -> Optional[str]:
    """Return the canonical yfinance symbol for an index, or None."""
    info = parse_index(symbol)
    return info.yfinance_symbol if info else None


def index_context(symbol: str) -> str:
    """Return prompt context for an index, or empty string for non-index."""
    info = parse_index(symbol)
    if not info:
        return ""

    return (
        f"The instrument is a market index: {info.name} ({info.yfinance_symbol}). "
        f"It tracks {info.components_desc}. "
        f"The most liquid ETF proxy is {info.benchmark_etf}. "
        "Interpret Buy/Overweight as bullish on the index (go long via ETF or "
        "futures); interpret Sell/Underweight as bearish (go short or reduce "
        "exposure); Hold means maintain current positioning. "
        "This is NOT an individual stock — do not use equity-specific concepts "
        "such as individual company earnings, dividends, insider transactions, "
        "balance sheets, or management quality. Instead focus on macro "
        "fundamentals: monetary policy, interest rates, inflation, economic "
        "growth, sector composition, market breadth, cross-asset flows, "
        "geopolitical risk, and broad risk sentiment."
    )


def index_macro_fundamentals(symbol: str, curr_date: str = None) -> str:
    """Return an index-specific fundamental-analysis scaffold."""
    info = parse_index(symbol)
    if not info:
        raise ValueError(f"not a recognized market index: {symbol}")

    date_line = f" as of {curr_date}" if curr_date else ""
    return (
        f"# Index Macro Fundamentals for {info.name} ({info.yfinance_symbol}){date_line}\n\n"
        f"This is a market index ({info.components_desc}), not an individual "
        "equity. Analyze through macro and market-structure fundamentals:\n"
        "- Monetary policy: central-bank rate path, quantitative tightening/"
        "easing, real rates, yield curve shape, and forward guidance.\n"
        "- Economic data: GDP growth, employment, inflation (CPI/PCE), PMIs, "
        "consumer confidence, retail sales, industrial production.\n"
        "- Corporate earnings season: aggregate earnings growth, revenue "
        "trends, margin compression/expansion, guidance revisions.\n"
        "- Sector composition & rotation: which sectors drive the index, "
        "rotation into/out of cyclicals vs defensives, mega-cap "
        "concentration risk.\n"
        "- Market breadth & internals: advance/decline line, new highs/lows, "
        "% of constituents above key moving averages.\n"
        "- Liquidity & flows: fund flows (ETF inflows/outflows), margin "
        "debt, buyback activity, options market positioning.\n"
        "- Cross-asset signals: dollar strength, bond yields, credit "
        "spreads, commodity prices, volatility (VIX).\n"
        "- Geopolitical & regulatory: trade policy, fiscal stimulus, "
        "elections, sanctions, regulatory changes.\n"
        f"Directional convention: Buy means bullish on {info.name}; "
        f"Sell means bearish on {info.name}."
    )


def index_not_applicable(symbol: str, data_name: str) -> str:
    """Return a 'not applicable' message for equity-only data on an index."""
    info = parse_index(symbol)
    display = f"{info.name} ({info.yfinance_symbol})" if info else symbol
    return (
        f"{data_name} is not applicable to market index {display}. Indices do "
        "not have individual company financial statements. Use macro "
        "fundamentals, monetary policy, economic data, sector composition, "
        "market breadth, and cross-asset signals instead."
    )
