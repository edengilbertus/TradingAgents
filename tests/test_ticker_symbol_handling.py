import unittest

import pytest

from cli.utils import normalize_ticker_symbol
from tradingagents.agents.utils.agent_utils import build_instrument_context


@pytest.mark.unit
class TickerSymbolHandlingTests(unittest.TestCase):
    def test_normalize_ticker_symbol_preserves_exchange_suffix(self):
        self.assertEqual(normalize_ticker_symbol(" cnc.to "), "CNC.TO")

    def test_normalize_ticker_symbol_accepts_forex_slash_pair(self):
        self.assertEqual(normalize_ticker_symbol(" eur/usd "), "EURUSD=X")

    def test_normalize_ticker_symbol_preserves_forex_yfinance_pair(self):
        self.assertEqual(normalize_ticker_symbol("gbpusd=x"), "GBPUSD=X")

    def test_build_instrument_context_mentions_exact_symbol(self):
        context = build_instrument_context("7203.T")
        self.assertIn("7203.T", context)
        self.assertIn("exchange suffix", context)

    def test_build_instrument_context_describes_forex_pair(self):
        context = build_instrument_context("EUR/USD")
        self.assertIn("EURUSD=X", context)
        self.assertIn("forex pair", context)
        self.assertIn("Base currency: EUR", context)
        self.assertIn("Quote currency: USD", context)
        self.assertIn("long EUR / short USD", context)


if __name__ == "__main__":
    unittest.main()
