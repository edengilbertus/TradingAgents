import pytest


@pytest.mark.unit
class TestForexPairParsing:
    def test_parse_yfinance_forex_symbol(self):
        from tradingagents.dataflows.forex import parse_forex_pair

        pair = parse_forex_pair("EURUSD=X")

        assert pair is not None
        assert pair.base == "EUR"
        assert pair.quote == "USD"
        assert pair.yfinance_symbol == "EURUSD=X"

    def test_parse_slash_forex_symbol(self):
        from tradingagents.dataflows.forex import parse_forex_pair

        pair = parse_forex_pair("gbp/jpy")

        assert pair is not None
        assert pair.base == "GBP"
        assert pair.quote == "JPY"
        assert pair.yfinance_symbol == "GBPJPY=X"

    def test_does_not_treat_equity_symbol_as_forex(self):
        from tradingagents.dataflows.forex import parse_forex_pair

        assert parse_forex_pair("MSFT") is None


@pytest.mark.unit
def test_alpha_vantage_stock_data_uses_fx_daily_for_forex_pairs(monkeypatch):
    from tradingagents.dataflows import alpha_vantage_stock

    captured = {}

    def fake_request(function_name, params):
        captured["function_name"] = function_name
        captured["params"] = params
        return "timestamp,open,high,low,close\n2024-01-02,1.1,1.2,1.0,1.15\n"

    monkeypatch.setattr(alpha_vantage_stock, "_make_api_request", fake_request)
    monkeypatch.setattr(
        alpha_vantage_stock,
        "_filter_csv_by_date_range",
        lambda csv_data, start_date, end_date: csv_data,
    )

    result = alpha_vantage_stock.get_stock("EUR/USD", "2024-01-01", "2024-01-31")

    assert "2024-01-02" in result
    assert captured["function_name"] == "FX_DAILY"
    assert captured["params"]["from_symbol"] == "EUR"
    assert captured["params"]["to_symbol"] == "USD"
    assert captured["params"]["datatype"] == "csv"
