import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
from types import SimpleNamespace

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
    ledger = Mock()
    mock_get_portfolio_summary.return_value = {
        "NetLiquidation": 0.0,
        "AvailableFunds": 0.0,
        "UnrealizedPnL": 0.0,
        "RealizedPnL": 0.0,
    }

    with patch("src.main.fetch_price", side_effect=Exception("API error")):
        await execute_trading_cycle(ib, agent, "AAPL", ledger)

    agent.analyze_market.assert_not_called()


@pytest.mark.asyncio
@patch("src.main.get_technical_context", return_value={"trend": "down"})
@patch("src.main.fetch_price", return_value=100.0)
@patch("src.main.place_market_order")
@patch("src.main.check_trade_viability")
@patch("src.main.get_portfolio_summary")
async def test_execute_trading_cycle_executes_sell_and_records_trade(
    mock_get_portfolio_summary,
    mock_check_trade_viability,
    mock_place_market_order,
    mock_fetch_price,
    mock_get_technical_context,
):
    ib = Mock()
    ib.reqPositionsAsync = AsyncMock(return_value=[])
    ib.qualifyContractsAsync = AsyncMock(return_value=None)
    agent = Mock()
    agent.analyze_market.return_value = {
        "decision": "SELL",
        "confidence": 90,
        "reasoning": "Exit signal",
    }
    ledger = Mock()
    ledger.virtual_cash = 0.0
    ledger.unrealized_pnl = 0.0
    ledger.realized_pnl = 0.0
    ledger.total_commissions_paid = 0.0

    mock_get_portfolio_summary.return_value = {
        "NetLiquidation": 100000.0,
        "AvailableFunds": 50000.0,
        "UnrealizedPnL": 100.0,
        "RealizedPnL": 50.0,
    }
    mock_check_trade_viability.return_value = {
        "approved": True,
        "quantity": 1,
        "reason": "Approved",
    }

    await execute_trading_cycle(ib, agent, "AAPL", ledger)

    mock_check_trade_viability.assert_called_once()
    mock_place_market_order.assert_called_once()
    ledger.record_trade.assert_called_once_with("SELL", 1, 100.0)


@pytest.mark.asyncio
@patch("src.main.get_technical_context", return_value={"trend": "flat"})
@patch("src.main.fetch_price", return_value=100.0)
@patch("src.main.get_portfolio_summary")
async def test_execute_trading_cycle_syncs_initial_positions_to_shadow_ledger(
    mock_get_portfolio_summary,
    mock_fetch_price,
    mock_get_technical_context,
):
    ib = Mock()
    ib.reqPositionsAsync = AsyncMock(return_value=[
        SimpleNamespace(
            contract=SimpleNamespace(symbol="AAPL"),
            position=3,
            avgCost="102.5",
        )
    ])
    agent = Mock()
    agent.analyze_market.return_value = {
        "decision": "HOLD",
        "confidence": 50,
        "reasoning": "No setup",
    }

    class LedgerState:
        def __init__(self):
            self.virtual_cash = 0.0
            self.unrealized_pnl = 0.0
            self.realized_pnl = 0.0
            self.total_commissions_paid = 0.0
            self._position_shares = 0
            self._position_cost = 0.0

        def record_trade(self, action, quantity, price):
            return None

    ledger = LedgerState()

    mock_get_portfolio_summary.return_value = {
        "NetLiquidation": 100000.0,
        "AvailableFunds": 50000.0,
        "UnrealizedPnL": 100.0,
        "RealizedPnL": 50.0,
    }

    await execute_trading_cycle(ib, agent, "AAPL", ledger)

    assert ledger.virtual_cash == 50000.0
    assert ledger._position_shares == 3
    assert ledger._position_cost == 307.5


@pytest.mark.asyncio
@patch("src.main.get_technical_context", return_value={"trend": "flat"})
@patch("src.main.fetch_price", return_value=100.0)
@patch("src.main.get_portfolio_summary")
async def test_execute_trading_cycle_ignores_short_positions_during_initial_sync(
    mock_get_portfolio_summary,
    mock_fetch_price,
    mock_get_technical_context,
):
    ib = Mock()
    ib.reqPositionsAsync = AsyncMock(
        return_value=[
            SimpleNamespace(
                contract=SimpleNamespace(symbol="AAPL"),
                position=-2,
                avgCost="99.0",
            )
        ]
    )
    agent = Mock()
    agent.analyze_market.return_value = {
        "decision": "HOLD",
        "confidence": 50,
        "reasoning": "No setup",
    }

    class LedgerState:
        def __init__(self):
            self.virtual_cash = 0.0
            self.unrealized_pnl = 0.0
            self.realized_pnl = 0.0
            self.total_commissions_paid = 0.0
            self._position_shares = 0
            self._position_cost = 0.0

        def record_trade(self, action, quantity, price):
            return None

    ledger = LedgerState()

    mock_get_portfolio_summary.return_value = {
        "NetLiquidation": 100000.0,
        "AvailableFunds": 50000.0,
        "UnrealizedPnL": 100.0,
        "RealizedPnL": 50.0,
    }

    await execute_trading_cycle(ib, agent, "AAPL", ledger)

    assert ledger.virtual_cash == 50000.0
    assert ledger._position_shares == 0
    assert ledger._position_cost == 0.0