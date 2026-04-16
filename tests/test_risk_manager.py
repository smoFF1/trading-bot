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