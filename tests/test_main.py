import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import src.main as main
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
@patch("src.main.get_recent_news")
@patch("src.main.get_technical_context")
@patch("src.main.fetch_price", return_value=0.0)
@patch("src.main.get_portfolio_summary")
async def test_execute_trading_cycle_returns_early_when_price_is_non_positive(
    mock_get_portfolio_summary,
    mock_fetch_price,
    mock_get_technical_context,
    mock_get_recent_news,
):
    ib = Mock()
    ib.reqPositionsAsync = AsyncMock(return_value=[])
    agent = Mock()
    ledger = Mock()
    ledger.virtual_cash = 1.0
    ledger.unrealized_pnl = 0.0
    ledger.realized_pnl = 0.0
    ledger.total_commissions_paid = 0.0

    mock_get_portfolio_summary.return_value = {
        "NetLiquidation": 100000.0,
        "AvailableFunds": 50000.0,
        "UnrealizedPnL": 100.0,
        "RealizedPnL": 50.0,
    }

    await execute_trading_cycle(ib, agent, "AAPL", ledger)

    mock_get_technical_context.assert_not_called()
    mock_get_recent_news.assert_not_called()
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
async def test_execute_trading_cycle_handles_invalid_avg_cost_in_initial_sync(
    mock_get_portfolio_summary,
    mock_fetch_price,
    mock_get_technical_context,
):
    ib = Mock()
    ib.reqPositionsAsync = AsyncMock(return_value=[
        SimpleNamespace(
            contract=SimpleNamespace(symbol="AAPL"),
            position=3,
            avgCost="invalid",
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

    assert ledger._position_shares == 3
    assert ledger._position_cost == 0.0


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


@pytest.mark.asyncio
@patch("src.main.asyncio.sleep", new_callable=AsyncMock)
@patch("src.main.get_recent_news", return_value="recent news")
@patch("src.main.get_technical_context", return_value="technical context")
@patch("src.main.fetch_price", return_value=100.0)
@patch("src.main.place_market_order")
@patch("src.main.check_trade_viability")
@patch("src.main.get_portfolio_summary")
async def test_execute_trading_cycle_buy_executes_order_and_records_trade(
    mock_get_portfolio_summary,
    mock_check_trade_viability,
    mock_place_market_order,
    mock_fetch_price,
    mock_get_technical_context,
    mock_get_recent_news,
    mock_sleep,
):
    ib = Mock()
    ib.reqPositionsAsync = AsyncMock(return_value=[])
    ib.qualifyContractsAsync = AsyncMock(return_value=None)
    agent = Mock()
    agent.analyze_market.return_value = {
        "decision": "BUY",
        "confidence": 90,
        "reasoning": "Strong setup",
    }
    ledger = Mock()
    ledger.virtual_cash = 0.0
    ledger.unrealized_pnl = 0.0
    ledger.realized_pnl = 0.0
    ledger.total_commissions_paid = 0.0
    ledger.record_trade = Mock()

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

    mock_place_market_order.assert_called_once()
    ledger.record_trade.assert_called_once_with("BUY", 1, 100.0)


@pytest.mark.asyncio
@patch("src.main.asyncio.sleep", new_callable=AsyncMock)
@patch("src.main.get_recent_news", return_value="recent news")
@patch("src.main.get_technical_context", return_value="technical context")
@patch("src.main.fetch_price", return_value=100.0)
@patch("src.main.place_market_order")
@patch("src.main.check_trade_viability")
@patch("src.main.get_portfolio_summary")
async def test_execute_trading_cycle_buy_rejection_skips_order(
    mock_get_portfolio_summary,
    mock_check_trade_viability,
    mock_place_market_order,
    mock_fetch_price,
    mock_get_technical_context,
    mock_get_recent_news,
    mock_sleep,
):
    ib = Mock()
    ib.reqPositionsAsync = AsyncMock(return_value=[])
    ib.qualifyContractsAsync = AsyncMock(return_value=None)
    agent = Mock()
    agent.analyze_market.return_value = {
        "decision": "BUY",
        "confidence": 90,
        "reasoning": "Strong setup",
    }
    ledger = Mock()
    ledger.virtual_cash = 0.0
    ledger.unrealized_pnl = 0.0
    ledger.realized_pnl = 0.0
    ledger.total_commissions_paid = 0.0
    ledger.record_trade = Mock()

    mock_get_portfolio_summary.return_value = {
        "NetLiquidation": 100000.0,
        "AvailableFunds": 50000.0,
        "UnrealizedPnL": 100.0,
        "RealizedPnL": 50.0,
    }
    mock_check_trade_viability.return_value = {
        "approved": False,
        "quantity": 1,
        "reason": "Rejected",
    }

    await execute_trading_cycle(ib, agent, "AAPL", ledger)

    mock_place_market_order.assert_not_called()
    ledger.record_trade.assert_not_called()


@pytest.mark.asyncio
@patch("src.main.asyncio.sleep", new_callable=AsyncMock)
@patch("src.main.get_recent_news", return_value="recent news")
@patch("src.main.get_technical_context", return_value="technical context")
@patch("src.main.fetch_price", return_value=100.0)
@patch("src.main.place_market_order")
@patch("src.main.check_trade_viability")
@patch("src.main.get_portfolio_summary")
async def test_execute_trading_cycle_buy_handles_ledger_exception(
    mock_get_portfolio_summary,
    mock_check_trade_viability,
    mock_place_market_order,
    mock_fetch_price,
    mock_get_technical_context,
    mock_get_recent_news,
    mock_sleep,
):
    ib = Mock()
    ib.reqPositionsAsync = AsyncMock(return_value=[])
    ib.qualifyContractsAsync = AsyncMock(return_value=None)
    agent = Mock()
    agent.analyze_market.return_value = {
        "decision": "BUY",
        "confidence": 90,
        "reasoning": "Strong setup",
    }
    ledger = Mock()
    ledger.virtual_cash = 0.0
    ledger.unrealized_pnl = 0.0
    ledger.realized_pnl = 0.0
    ledger.total_commissions_paid = 0.0
    ledger.record_trade = Mock(side_effect=Exception("ledger boom"))

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

    mock_place_market_order.assert_called_once()
    ledger.record_trade.assert_called_once_with("BUY", 1, 100.0)


@pytest.mark.asyncio
@patch("src.main.asyncio.sleep", new_callable=AsyncMock)
@patch("src.main.get_recent_news", return_value="recent news")
@patch("src.main.get_technical_context", return_value="technical context")
@patch("src.main.fetch_price", return_value=100.0)
@patch("src.main.place_market_order")
@patch("src.main.check_trade_viability")
@patch("src.main.get_portfolio_summary")
async def test_execute_trading_cycle_sell_handles_ledger_exception(
    mock_get_portfolio_summary,
    mock_check_trade_viability,
    mock_place_market_order,
    mock_fetch_price,
    mock_get_technical_context,
    mock_get_recent_news,
    mock_sleep,
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
    ledger.record_trade = Mock(side_effect=Exception("ledger boom"))

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

    mock_place_market_order.assert_called_once()
    ledger.record_trade.assert_called_once_with("SELL", 1, 100.0)


@pytest.mark.asyncio
@patch("src.main.asyncio.sleep", new_callable=AsyncMock)
@patch("src.main.get_recent_news", return_value="recent news")
@patch("src.main.get_technical_context", return_value="technical context")
@patch("src.main.fetch_price", return_value=100.0)
@patch("src.main.place_market_order")
@patch("src.main.check_trade_viability")
@patch("src.main.get_portfolio_summary")
async def test_execute_trading_cycle_sell_rejection_skips_order(
    mock_get_portfolio_summary,
    mock_check_trade_viability,
    mock_place_market_order,
    mock_fetch_price,
    mock_get_technical_context,
    mock_get_recent_news,
    mock_sleep,
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
    ledger.record_trade = Mock()

    mock_get_portfolio_summary.return_value = {
        "NetLiquidation": 100000.0,
        "AvailableFunds": 50000.0,
        "UnrealizedPnL": 100.0,
        "RealizedPnL": 50.0,
    }
    mock_check_trade_viability.return_value = {
        "approved": False,
        "quantity": 1,
        "reason": "Rejected",
    }

    await execute_trading_cycle(ib, agent, "AAPL", ledger)

    mock_place_market_order.assert_not_called()
    ledger.record_trade.assert_not_called()


@pytest.mark.asyncio
@patch("src.main.get_portfolio_summary", side_effect=Exception("Fatal error"))
async def test_execute_trading_cycle_handles_outer_exception_gracefully(mock_get_portfolio_summary):
    ib = Mock()
    agent = Mock()
    ledger = Mock()

    await execute_trading_cycle(ib, agent, "AAPL", ledger)

    agent.analyze_market.assert_not_called()


@pytest.mark.asyncio
@patch("src.main.fetch_price", return_value=0.0)
@patch("src.main.get_portfolio_summary")
async def test_execute_trading_cycle_handles_initial_position_sync_exception(
    mock_get_portfolio_summary,
    mock_fetch_price,
):
    ib = Mock()
    ib.reqPositionsAsync = AsyncMock(side_effect=Exception("positions failed"))
    agent = Mock()
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

    await execute_trading_cycle(ib, agent, "AAPL", ledger)

    agent.analyze_market.assert_not_called()


@pytest.mark.asyncio
@patch("src.main.asyncio.sleep", new_callable=AsyncMock)
async def test_connect_ibkr_retries_after_connection_refused(mock_sleep):
    connect_mock = AsyncMock(side_effect=[ConnectionRefusedError("nope"), None])
    with patch("src.main.get_wsl_host_ip", return_value="127.0.0.1"), patch.object(
        main.ib,
        "connectAsync",
        new=connect_mock,
    ):
        await main.connect_ibkr()

    assert connect_mock.await_count == 2
    mock_sleep.assert_awaited_once_with(5)


@pytest.mark.asyncio
@patch("src.main.asyncio.sleep", new_callable=AsyncMock)
async def test_trading_loop_waits_when_ib_is_not_connected_and_stops(mock_sleep):
    main.bot_running = True

    call_count = {"count": 0}

    def _is_connected():
        call_count["count"] += 1
        main.bot_running = False
        return False

    with patch.object(main.ib, "isConnected", side_effect=_is_connected), patch(
        "src.main.execute_trading_cycle",
        new=Mock(),
    ):
        await main.trading_loop()

    assert call_count["count"] == 1
    mock_sleep.assert_awaited_once_with(10)


@pytest.mark.asyncio
@patch("src.main.asyncio.sleep", new_callable=AsyncMock)
async def test_trading_loop_runs_cycle_when_connected_then_stops(mock_sleep):
    main.bot_running = True

    async def _execute_cycle(*args, **kwargs):
        main.bot_running = False

    with patch.object(main.ib, "isConnected", return_value=True), patch(
        "src.main.execute_trading_cycle",
        new=AsyncMock(side_effect=_execute_cycle),
    ) as mock_execute_cycle:
        await main.trading_loop()

    mock_execute_cycle.assert_awaited_once()
    mock_sleep.assert_awaited_once_with(300)


@pytest.mark.asyncio
async def test_lifespan_disconnects_ib_on_shutdown():
    main.bot_running = True
    main.bot_task = None

    with patch("src.main.connect_ibkr", new=Mock(return_value=None)), patch(
        "src.main.asyncio.create_task",
        return_value=Mock(),
    ), patch.object(main.ib, "isConnected", return_value=True), patch.object(
        main.ib,
        "disconnect",
        return_value=None,
    ) as mock_disconnect:
        async with main.lifespan(Mock()):
            pass

    mock_disconnect.assert_called_once()