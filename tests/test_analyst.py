import sys
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.analyst import get_technical_context


@pytest.mark.asyncio
async def test_get_technical_context_returns_summary_with_enough_data():
    close_prices = [float(price) for price in range(100, 121)]
    history = pd.DataFrame({"Close": close_prices})
    mock_ticker = Mock()
    mock_ticker.history.return_value = history

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr("src.analyst.yf.Ticker", Mock(return_value=mock_ticker))
        result = await get_technical_context("AAPL")

    assert "20-day SMA" in result
    assert "RSI is" in result
    assert "Trend is bullish" in result


@pytest.mark.asyncio
async def test_get_technical_context_handles_insufficient_data_gracefully():
    history = pd.DataFrame({"Close": [100.0]})
    mock_ticker = Mock()
    mock_ticker.history.return_value = history

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr("src.analyst.yf.Ticker", Mock(return_value=mock_ticker))
        result = await get_technical_context("AAPL")

    assert "20-day SMA is unavailable" in result
    assert "RSI is unavailable" in result