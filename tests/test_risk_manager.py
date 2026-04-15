import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.risk_manager import check_trade_viability


@pytest.mark.asyncio
async def test_check_trade_viability_approves_buy_when_cash_is_sufficient():
	ib = Mock()
	ib.accountValues.return_value = [SimpleNamespace(tag="AvailableFunds", currency="USD", value="1000")]
	ib.positions.return_value = []

	result = await check_trade_viability(ib, "AAPL", "BUY", 100.0, 5)

	assert result == {
		"approved": True,
		"quantity": 5,
		"reason": "Approved: $500.00 required, $1000.00 available.",
	}


@pytest.mark.asyncio
async def test_check_trade_viability_rejects_buy_when_cash_is_insufficient():
	ib = Mock()
	ib.accountValues.return_value = [SimpleNamespace(tag="AvailableFunds", currency="USD", value="100")]
	ib.positions.return_value = []

	result = await check_trade_viability(ib, "AAPL", "BUY", 100.0, 2)

	assert result["approved"] is False
	assert result["quantity"] == 2
	assert "required" in result["reason"]


@pytest.mark.asyncio
async def test_check_trade_viability_approves_sell_when_position_is_sufficient():
	ib = Mock()
	ib.accountValues.return_value = []
	ib.positions.return_value = [SimpleNamespace(contract=SimpleNamespace(symbol="AAPL"), position=3)]

	result = await check_trade_viability(ib, "AAPL", "SELL", 100.0, 2)

	assert result == {
		"approved": True,
		"quantity": 2,
		"reason": "Approved: position of 3 covers requested sell of 2.",
	}


@pytest.mark.asyncio
async def test_check_trade_viability_rejects_sell_when_position_is_insufficient():
	ib = Mock()
	ib.accountValues.return_value = []
	ib.positions.return_value = [SimpleNamespace(contract=SimpleNamespace(symbol="AAPL"), position=1)]

	result = await check_trade_viability(ib, "AAPL", "SELL", 100.0, 2)

	assert result["approved"] is False
	assert result["quantity"] == 2
	assert "below requested sell" in result["reason"]