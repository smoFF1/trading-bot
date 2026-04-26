import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.risk_manager import check_trade_viability


@pytest.mark.asyncio
async def test_check_trade_viability_approves_buy_when_cash_is_sufficient():
	ib = Mock()
	contract = Mock()
	contract.symbol = "AAPL"
	ib.accountValues.return_value = [SimpleNamespace(tag="AvailableFunds", currency="USD", value="1000")]
	ib.positions.return_value = []
	ib.whatIfOrderAsync = AsyncMock(return_value=SimpleNamespace(maxCommission=1.50))

	result = await check_trade_viability(ib, contract, "BUY", 100.0, 5)

	assert result == {
		"approved": True,
		"quantity": 5,
		"reason": "Approved: $501.50 required (incl. $1.50 commission), $1000.00 available.",
	}


@pytest.mark.asyncio
async def test_check_trade_viability_rejects_buy_when_cash_is_insufficient():
	ib = Mock()
	contract = Mock()
	contract.symbol = "AAPL"
	ib.accountValues.return_value = [SimpleNamespace(tag="AvailableFunds", currency="USD", value="100")]
	ib.positions.return_value = []
	ib.whatIfOrderAsync = AsyncMock(return_value=SimpleNamespace(maxCommission=1.50))

	result = await check_trade_viability(ib, contract, "BUY", 100.0, 2)

	assert result["approved"] is False
	assert result["quantity"] == 2
	assert "Rejected: $201.50 required" in result["reason"]
	assert "incl. $1.50 commission" in result["reason"]


@pytest.mark.asyncio
async def test_check_trade_viability_approves_sell_when_position_is_sufficient():
	ib = Mock()
	contract = Mock()
	contract.symbol = "AAPL"
	ib.accountValues.return_value = []
	ib.positions.return_value = [SimpleNamespace(contract=SimpleNamespace(symbol="AAPL"), position=3)]
	ib.whatIfOrderAsync = AsyncMock(return_value=SimpleNamespace(maxCommission=1.50))

	result = await check_trade_viability(ib, contract, "SELL", 100.0, 2)

	assert result == {
		"approved": True,
		"quantity": 2,
		"reason": "Approved: position of 3 covers requested sell of 2.",
	}


@pytest.mark.asyncio
async def test_check_trade_viability_rejects_sell_when_position_is_insufficient():
	ib = Mock()
	contract = Mock()
	contract.symbol = "AAPL"
	ib.accountValues.return_value = []
	ib.positions.return_value = [SimpleNamespace(contract=SimpleNamespace(symbol="AAPL"), position=1)]
	ib.whatIfOrderAsync = AsyncMock(return_value=SimpleNamespace(maxCommission=1.50))

	result = await check_trade_viability(ib, contract, "SELL", 100.0, 2)

	assert result["approved"] is False
	assert result["quantity"] == 2
	assert "below requested sell" in result["reason"]


@pytest.mark.asyncio
async def test_check_trade_viability_uses_fallback_commission_when_whatif_returns_zero():
	ib = Mock()
	contract = Mock()
	contract.symbol = "AAPL"
	ib.accountValues.return_value = [SimpleNamespace(tag="AvailableFunds", currency="USD", value="1000")]
	ib.positions.return_value = []
	ib.whatIfOrderAsync = AsyncMock(return_value=SimpleNamespace(maxCommission=0.0, minCommission=0.0, commission=0.0))

	result = await check_trade_viability(ib, contract, "BUY", 100.0, 10)

	assert result["approved"] is False
	assert result["quantity"] == 10
	assert "incl. $0.45 commission" in result["reason"]


@pytest.mark.asyncio
async def test_check_trade_viability_falls_back_to_zero_commission_when_calculation_fails():
	ib = Mock()
	contract = Mock()
	contract.symbol = "AAPL"
	ib.accountValues.return_value = [SimpleNamespace(tag="AvailableFunds", currency="USD", value="1000")]
	ib.positions.return_value = []
	ib.whatIfOrderAsync = AsyncMock(return_value=SimpleNamespace(maxCommission=None, minCommission=None, commission=None))

	with pytest.MonkeyPatch.context() as monkeypatch:
		monkeypatch.setattr("src.risk_manager.calculate_realistic_commission", Mock(side_effect=ValueError("bad commission")))
		result = await check_trade_viability(ib, contract, "BUY", 100.0, 1)

	assert result == {
		"approved": True,
		"quantity": 1,
		"reason": "Approved: $100.00 required (incl. $0.00 commission), $1000.00 available.",
	}


@pytest.mark.asyncio
async def test_check_trade_viability_defaults_available_cash_to_zero_for_invalid_value():
	ib = Mock()
	contract = Mock()
	contract.symbol = "AAPL"
	ib.accountValues.return_value = [SimpleNamespace(tag="AvailableFunds", currency="USD", value="invalid")]
	ib.positions.return_value = []
	ib.whatIfOrderAsync = AsyncMock(return_value=SimpleNamespace(maxCommission=1.50))

	result = await check_trade_viability(ib, contract, "BUY", 100.0, 1)

	assert result["approved"] is False
	assert result["quantity"] == 1
	assert "$101.50 required" in result["reason"]
	assert "$0.00 available" in result["reason"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
	"order_state",
	[
		SimpleNamespace(maxCommission=None, minCommission=None, commission="invalid"),
		SimpleNamespace(maxCommission="invalid", minCommission="invalid", commission=None),
	],
)
async def test_check_trade_viability_uses_fallback_commission_for_invalid_whatif_values(order_state):
	ib = Mock()
	contract = Mock()
	contract.symbol = "AAPL"
	ib.accountValues.return_value = [SimpleNamespace(tag="AvailableFunds", currency="USD", value="1000")]
	ib.positions.return_value = []
	ib.whatIfOrderAsync = AsyncMock(return_value=order_state)

	result = await check_trade_viability(ib, contract, "BUY", 100.0, 10)

	assert result["approved"] is False
	assert result["quantity"] == 10
	assert "incl. $0.45 commission" in result["reason"]


@pytest.mark.asyncio
async def test_check_trade_viability_defaults_position_to_zero_for_invalid_position_value():
	ib = Mock()
	contract = Mock()
	contract.symbol = "AAPL"
	ib.accountValues.return_value = []
	ib.positions.return_value = [SimpleNamespace(contract=SimpleNamespace(symbol="AAPL"), position="invalid")]
	ib.whatIfOrderAsync = AsyncMock(return_value=SimpleNamespace(maxCommission=1.50))

	result = await check_trade_viability(ib, contract, "SELL", 100.0, 1)

	assert result["approved"] is False
	assert result["quantity"] == 1
	assert "position of 0 is below requested sell of 1" in result["reason"]


@pytest.mark.asyncio
async def test_check_trade_viability_skips_non_matching_positions_before_finding_target_symbol():
	ib = Mock()
	contract = Mock()
	contract.symbol = "AAPL"
	ib.accountValues.return_value = []
	ib.positions.return_value = [
		SimpleNamespace(contract=SimpleNamespace(symbol="TSLA"), position=99),
		SimpleNamespace(contract=SimpleNamespace(symbol="AAPL"), position=3),
	]
	ib.whatIfOrderAsync = AsyncMock(return_value=SimpleNamespace(maxCommission=1.50))

	result = await check_trade_viability(ib, contract, "SELL", 100.0, 2)

	assert result == {
		"approved": True,
		"quantity": 2,
		"reason": "Approved: position of 3 covers requested sell of 2.",
	}


@pytest.mark.asyncio
async def test_check_trade_viability_rejects_unsupported_action():
	ib = Mock()
	contract = Mock()
	contract.symbol = "AAPL"
	ib.accountValues.return_value = [SimpleNamespace(tag="AvailableFunds", currency="USD", value="1000")]
	ib.positions.return_value = []
	ib.whatIfOrderAsync = AsyncMock(return_value=SimpleNamespace(maxCommission=1.50))

	result = await check_trade_viability(ib, contract, "HOLD", 100.0, 1)

	assert result == {
		"approved": False,
		"quantity": 1,
		"reason": "Unsupported action. Use BUY or SELL.",
	}