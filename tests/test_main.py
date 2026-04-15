import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from src.main import fetch_price, execute_trading_cycle


@pytest.mark.asyncio
async def test_fetch_price_returns_mocked_last_price():
    mock_ticker = Mock()
    mock_ticker.fast_info = {"lastPrice": 150.5}

    with patch("src.main.yf.Ticker", return_value=mock_ticker) as mock_ticker_cls:
        result = await fetch_price("AAPL")

    assert result == 150.5
    mock_ticker_cls.assert_called_once_with("AAPL")


@pytest.mark.asyncio
@patch("src.main.get_portfolio_summary")
async def test_execute_trading_cycle_handles_price_fetch_error(mock_get_portfolio_summary):
    ib = Mock()
    agent = Mock()
    mock_get_portfolio_summary.return_value = {
        "NetLiquidation": 0.0,
        "AvailableFunds": 0.0,
        "UnrealizedPnL": 0.0,
        "RealizedPnL": 0.0,
    }

    with patch("src.main.fetch_price", side_effect=Exception("API error")):
        await execute_trading_cycle(ib, agent, "AAPL")

    agent.analyze_market.assert_not_called()