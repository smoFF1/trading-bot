import sys
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.analyst import _format_value, get_technical_context


def _make_history(close_prices):
    return pd.DataFrame({"Close": close_prices})


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


def test_format_value_returns_unavailable_for_none():
    assert _format_value(None) == "unavailable"


@pytest.mark.asyncio
async def test_get_technical_context_handles_empty_history():
    mock_ticker = Mock()
    mock_ticker.history.return_value = pd.DataFrame()

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr("src.analyst.yf.Ticker", Mock(return_value=mock_ticker))
        result = await get_technical_context("AAPL")

    assert result == "Technical data for AAPL is unavailable."


@pytest.mark.asyncio
async def test_get_technical_context_handles_missing_close_column():
    mock_ticker = Mock()
    mock_ticker.history.return_value = pd.DataFrame({"Open": [100.0, 101.0]})

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr("src.analyst.yf.Ticker", Mock(return_value=mock_ticker))
        result = await get_technical_context("AAPL")

    assert result == "Technical data for AAPL is unavailable."


@pytest.mark.asyncio
async def test_get_technical_context_handles_unparsable_close_values():
    mock_ticker = Mock()
    mock_ticker.history.return_value = pd.DataFrame({"Close": ["invalid", "data"]})

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr("src.analyst.yf.Ticker", Mock(return_value=mock_ticker))
        result = await get_technical_context("AAPL")

    assert result == "Technical data for AAPL is unavailable."


@pytest.mark.asyncio
async def test_get_technical_context_marks_rsi_overbought():
    history = _make_history([float(price) for price in range(1, 31)])
    mock_ticker = Mock()
    mock_ticker.history.return_value = history

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr("src.analyst.yf.Ticker", Mock(return_value=mock_ticker))
        result = await get_technical_context("AAPL")

    assert "RSI is 100 (Overbought)" in result


@pytest.mark.asyncio
async def test_get_technical_context_marks_rsi_oversold():
    history = _make_history([float(price) for price in range(30, 0, -1)])
    mock_ticker = Mock()
    mock_ticker.history.return_value = history

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr("src.analyst.yf.Ticker", Mock(return_value=mock_ticker))
        result = await get_technical_context("AAPL")

    assert "RSI is 0 (Oversold)" in result


@pytest.mark.asyncio
async def test_get_technical_context_marks_rsi_neutral():
    history = _make_history([
        100.0, 101.0, 100.5, 101.5, 101.0, 102.0, 101.5, 102.5, 102.0, 103.0,
        102.5, 103.5, 103.0, 104.0, 103.5, 104.5, 104.0, 105.0, 104.5, 105.5,
        105.0, 106.0, 105.5, 106.5, 106.0, 107.0, 106.5, 107.5, 107.0, 107.5,
    ])
    mock_ticker = Mock()
    mock_ticker.history.return_value = history

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr("src.analyst.yf.Ticker", Mock(return_value=mock_ticker))
        result = await get_technical_context("AAPL")

    assert "RSI is" in result
    assert "(Neutral)" in result


@pytest.mark.asyncio
async def test_get_technical_context_uses_neutral_trend_when_price_equals_sma20():
    history = _make_history([100.0] * 20)
    mock_ticker = Mock()
    mock_ticker.history.return_value = history

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr("src.analyst.yf.Ticker", Mock(return_value=mock_ticker))
        result = await get_technical_context("AAPL")

    assert "equal to the 20-day SMA" in result
    assert "Trend is neutral." in result