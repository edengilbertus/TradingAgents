"""Unit tests for market index support.

Mirrors test_forex_support.py but covers the indices detection layer,
Alpha Vantage routing, and CLI normalization for index instruments.
"""
import pytest


# ── parse_index tests ──────────────────────────────────────────────────────


@pytest.mark.unit
class TestIndexParsing:
    def test_parse_broker_alias(self):
        from tradingagents.dataflows.indices import parse_index

        info = parse_index("US30")
        assert info is not None
        assert info.yfinance_symbol == "^DJI"
        assert info.name == "Dow Jones Industrial Average"
        assert info.benchmark_etf == "DIA"

    def test_parse_yfinance_symbol(self):
        from tradingagents.dataflows.indices import parse_index

        info = parse_index("^GSPC")
        assert info is not None
        assert info.name == "S&P 500"
        assert info.yfinance_symbol == "^GSPC"

    def test_parse_case_insensitive(self):
        from tradingagents.dataflows.indices import parse_index

        info = parse_index("nasdaq")
        assert info is not None
        assert info.yfinance_symbol == "^IXIC"

    def test_parse_us100_alias(self):
        from tradingagents.dataflows.indices import parse_index

        info = parse_index("NAS100")
        assert info is not None
        assert info.yfinance_symbol == "^NDX"
        assert info.benchmark_etf == "QQQ"

    def test_does_not_treat_equity_as_index(self):
        from tradingagents.dataflows.indices import parse_index

        assert parse_index("AAPL") is None
        assert parse_index("MSFT") is None
        assert parse_index("SPY") is None  # ETF, not an index

    def test_does_not_treat_forex_as_index(self):
        from tradingagents.dataflows.indices import parse_index

        assert parse_index("EURUSD=X") is None
        assert parse_index("EUR/USD") is None


# ── normalize_index_symbol tests ───────────────────────────────────────────


@pytest.mark.unit
class TestNormalizeIndexSymbol:
    def test_returns_canonical_yfinance_symbol(self):
        from tradingagents.dataflows.indices import normalize_index_symbol

        assert normalize_index_symbol("US500") == "^GSPC"
        assert normalize_index_symbol("DOW") == "^DJI"
        assert normalize_index_symbol("NIKKEI") == "^N225"

    def test_returns_none_for_non_index(self):
        from tradingagents.dataflows.indices import normalize_index_symbol

        assert normalize_index_symbol("AAPL") is None
        assert normalize_index_symbol("EUR/USD") is None


# ── index_macro_fundamentals tests ─────────────────────────────────────────


@pytest.mark.unit
class TestIndexMacroFundamentals:
    def test_returns_scaffold_with_index_details(self):
        from tradingagents.dataflows.indices import index_macro_fundamentals

        result = index_macro_fundamentals("^DJI", "2024-06-15")
        assert "Dow Jones Industrial Average" in result
        assert "^DJI" in result
        assert "2024-06-15" in result
        assert "monetary policy" in result.lower()

    def test_raises_for_non_index(self):
        from tradingagents.dataflows.indices import index_macro_fundamentals

        with pytest.raises(ValueError, match="not a recognized market index"):
            index_macro_fundamentals("AAPL")


# ── index_not_applicable tests ─────────────────────────────────────────────


@pytest.mark.unit
class TestIndexNotApplicable:
    def test_returns_clear_message(self):
        from tradingagents.dataflows.indices import index_not_applicable

        result = index_not_applicable("^DJI", "Balance sheet data")
        assert "Balance sheet data" in result
        assert "not applicable" in result
        assert "Dow Jones" in result


# ── index_context tests ───────────────────────────────────────────────────


@pytest.mark.unit
class TestIndexContext:
    def test_returns_context_for_known_index(self):
        from tradingagents.dataflows.indices import index_context

        ctx = index_context("^NDX")
        assert "NASDAQ-100" in ctx
        assert "^NDX" in ctx
        assert "QQQ" in ctx

    def test_returns_empty_for_non_index(self):
        from tradingagents.dataflows.indices import index_context

        assert index_context("AAPL") == ""


# ── Alpha Vantage adapter tests ────────────────────────────────────────────


@pytest.mark.unit
def test_alpha_vantage_fundamentals_returns_macro_for_index(monkeypatch):
    """get_fundamentals should return the macro scaffold for index tickers."""
    from tradingagents.dataflows import alpha_vantage_fundamentals

    # The function should detect the index and NOT call Alpha Vantage API
    result = alpha_vantage_fundamentals.get_fundamentals("US30", "2024-06-15")
    assert "Dow Jones Industrial Average" in result
    assert "monetary policy" in result.lower()


@pytest.mark.unit
def test_alpha_vantage_balance_sheet_not_applicable_for_index():
    from tradingagents.dataflows import alpha_vantage_fundamentals

    result = alpha_vantage_fundamentals.get_balance_sheet("^GSPC")
    assert "not applicable" in result


@pytest.mark.unit
def test_alpha_vantage_cashflow_not_applicable_for_index():
    from tradingagents.dataflows import alpha_vantage_fundamentals

    result = alpha_vantage_fundamentals.get_cashflow("NASDAQ100")
    assert "not applicable" in result


@pytest.mark.unit
def test_alpha_vantage_income_not_applicable_for_index():
    from tradingagents.dataflows import alpha_vantage_fundamentals

    result = alpha_vantage_fundamentals.get_income_statement("DAX")
    assert "not applicable" in result


@pytest.mark.unit
def test_alpha_vantage_stock_uses_etf_proxy_for_index(monkeypatch):
    """get_stock should use the benchmark ETF symbol for AV API calls."""
    from tradingagents.dataflows import alpha_vantage_stock

    captured = {}

    def fake_request(function_name, params):
        captured["function_name"] = function_name
        captured["params"] = params
        return "timestamp,open,high,low,close\n2024-01-02,35000,35100,34900,35050\n"

    monkeypatch.setattr(alpha_vantage_stock, "_make_api_request", fake_request)
    monkeypatch.setattr(
        alpha_vantage_stock,
        "_filter_csv_by_date_range",
        lambda csv_data, start_date, end_date: csv_data,
    )

    result = alpha_vantage_stock.get_stock("US30", "2024-01-01", "2024-01-31")

    assert "2024-01-02" in result
    assert captured["function_name"] == "TIME_SERIES_DAILY_ADJUSTED"
    assert captured["params"]["symbol"] == "DIA"  # ETF proxy for Dow Jones


@pytest.mark.unit
def test_alpha_vantage_insider_transactions_not_applicable_for_index():
    from tradingagents.dataflows import alpha_vantage_news

    result = alpha_vantage_news.get_insider_transactions("^DJI")
    assert "not applicable" in result


@pytest.mark.unit
def test_alpha_vantage_indicator_uses_etf_for_index(monkeypatch):
    """get_indicator should resolve index to benchmark ETF."""
    from tradingagents.dataflows import alpha_vantage_indicator

    captured = {}

    def fake_request(function_name, params):
        captured["function_name"] = function_name
        captured["params"] = params
        return "time,RSI\n2024-01-02,55.0\n"

    monkeypatch.setattr(alpha_vantage_indicator, "_make_api_request", fake_request)

    alpha_vantage_indicator.get_indicator(
        "US500", "rsi", "2024-01-03", 5
    )

    assert captured["params"]["symbol"] == "SPY"  # ETF proxy for S&P 500


# ── CLI normalization tests ────────────────────────────────────────────────


@pytest.mark.unit
class TestCLINormalization:
    def test_normalize_index_alias(self):
        from cli.utils import normalize_ticker_symbol

        assert normalize_ticker_symbol("us30") == "^DJI"
        assert normalize_ticker_symbol("nasdaq") == "^IXIC"
        assert normalize_ticker_symbol("US500") == "^GSPC"

    def test_normalize_preserves_equity(self):
        from cli.utils import normalize_ticker_symbol

        assert normalize_ticker_symbol("aapl") == "AAPL"
        assert normalize_ticker_symbol("CNC.TO") == "CNC.TO"

    def test_normalize_preserves_forex(self):
        from cli.utils import normalize_ticker_symbol

        result = normalize_ticker_symbol("EUR/USD")
        assert result == "EURUSD=X"


# ── build_instrument_context integration ───────────────────────────────────


@pytest.mark.unit
def test_build_instrument_context_for_index():
    from tradingagents.agents.utils.agent_utils import build_instrument_context

    ctx = build_instrument_context("US30")
    assert "Dow Jones" in ctx
    assert "^DJI" in ctx


@pytest.mark.unit
def test_build_instrument_context_for_canonical_index():
    from tradingagents.agents.utils.agent_utils import build_instrument_context

    ctx = build_instrument_context("^GSPC")
    assert "S&P 500" in ctx
