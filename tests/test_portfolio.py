import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.portfolio import get_portfolio_summary


@pytest.mark.asyncio
async def test_get_portfolio_summary_extracts_values():
    ib = Mock()
    net_liquidation = Mock(tag="NetLiquidation", currency="USD", value="105000.25")
    available_funds = Mock(tag="AvailableFunds", currency="USD", value="55000.10")
    unrealized_pnl = Mock(tag="UnrealizedPnL", currency="USD", value="-1250.75")
    realized_pnl = Mock(tag="RealizedPnL", currency="USD", value="300.50")
    ib.accountValues.return_value = [
        net_liquidation,
        available_funds,
        unrealized_pnl,
        realized_pnl,
    ]

    summary = await get_portfolio_summary(ib)

    assert summary == {
        "NetLiquidation": 105000.25,
        "AvailableFunds": 55000.10,
        "UnrealizedPnL": -1250.75,
        "RealizedPnL": 300.50,
    }


@pytest.mark.asyncio
async def test_get_portfolio_summary_defaults_to_zero_when_account_values_empty():
    ib = Mock()
    ib.accountValues.return_value = []

    summary = await get_portfolio_summary(ib)

    assert summary == {
        "NetLiquidation": 0.0,
        "AvailableFunds": 0.0,
        "UnrealizedPnL": 0.0,
        "RealizedPnL": 0.0,
    }