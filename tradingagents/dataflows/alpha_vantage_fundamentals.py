from .alpha_vantage_common import _make_api_request
from .forex import forex_macro_fundamentals, forex_not_applicable, parse_forex_pair
from .indices import index_macro_fundamentals, index_not_applicable, parse_index


def _filter_reports_by_date(result, curr_date: str):
    """Filter annualReports/quarterlyReports to exclude entries after curr_date.

    Prevents look-ahead bias by removing fiscal periods that end after
    the simulation's current date.
    """
    if not curr_date or not isinstance(result, dict):
        return result
    for key in ("annualReports", "quarterlyReports"):
        if key in result:
            result[key] = [
                r for r in result[key]
                if r.get("fiscalDateEnding", "") <= curr_date
            ]
    return result


def get_fundamentals(ticker: str, curr_date: str = None) -> str:
    """
    Retrieve comprehensive fundamental data for a given ticker symbol using Alpha Vantage.

    Args:
        ticker (str): Ticker symbol of the company
        curr_date (str): Current date you are trading at, yyyy-mm-dd (not used for Alpha Vantage)

    Returns:
        str: Company overview data including financial ratios and key metrics
    """
    forex_pair = parse_forex_pair(ticker)
    if forex_pair:
        macro_context = forex_macro_fundamentals(forex_pair.yfinance_symbol, curr_date)
        exchange_rate = _make_api_request(
            "CURRENCY_EXCHANGE_RATE",
            {
                "from_currency": forex_pair.base,
                "to_currency": forex_pair.quote,
            },
        )
        return f"{macro_context}\n\n# Alpha Vantage Current Exchange Rate\n\n{exchange_rate}"

    index_info = parse_index(ticker)
    if index_info:
        return index_macro_fundamentals(index_info.yfinance_symbol, curr_date)

    params = {
        "symbol": ticker,
    }

    return _make_api_request("OVERVIEW", params)


def get_balance_sheet(ticker: str, freq: str = "quarterly", curr_date: str = None):
    """Retrieve balance sheet data for a given ticker symbol using Alpha Vantage."""
    forex_pair = parse_forex_pair(ticker)
    if forex_pair:
        return forex_not_applicable(forex_pair.yfinance_symbol, "Balance sheet data")
    index_info = parse_index(ticker)
    if index_info:
        return index_not_applicable(index_info.yfinance_symbol, "Balance sheet data")

    result = _make_api_request("BALANCE_SHEET", {"symbol": ticker})
    return _filter_reports_by_date(result, curr_date)


def get_cashflow(ticker: str, freq: str = "quarterly", curr_date: str = None):
    """Retrieve cash flow statement data for a given ticker symbol using Alpha Vantage."""
    forex_pair = parse_forex_pair(ticker)
    if forex_pair:
        return forex_not_applicable(forex_pair.yfinance_symbol, "Cash flow data")
    index_info = parse_index(ticker)
    if index_info:
        return index_not_applicable(index_info.yfinance_symbol, "Cash flow data")

    result = _make_api_request("CASH_FLOW", {"symbol": ticker})
    return _filter_reports_by_date(result, curr_date)


def get_income_statement(ticker: str, freq: str = "quarterly", curr_date: str = None):
    """Retrieve income statement data for a given ticker symbol using Alpha Vantage."""
    forex_pair = parse_forex_pair(ticker)
    if forex_pair:
        return forex_not_applicable(forex_pair.yfinance_symbol, "Income statement data")
    index_info = parse_index(ticker)
    if index_info:
        return index_not_applicable(index_info.yfinance_symbol, "Income statement data")

    result = _make_api_request("INCOME_STATEMENT", {"symbol": ticker})
    return _filter_reports_by_date(result, curr_date)
