import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from src.main import fetch_price


@pytest.mark.asyncio
async def test_fetch_price_returns_mocked_last_price():
    mock_ticker = Mock()
    mock_ticker.fast_info = {"lastPrice": 150.5}

    with patch("src.main.yf.Ticker", return_value=mock_ticker) as mock_ticker_cls:
        result = await fetch_price("AAPL")

    assert result == 150.5
    mock_ticker_cls.assert_called_once_with("AAPL")