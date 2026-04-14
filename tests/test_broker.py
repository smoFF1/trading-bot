import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.broker import place_market_order


@pytest.mark.asyncio
async def test_place_market_order_buy_success():
    ib = Mock()
    contract = Mock()
    expected_trade = Mock()
    ib.placeOrder.return_value = expected_trade

    result = await place_market_order(ib, contract, "BUY", 1)

    assert result is expected_trade
    ib.placeOrder.assert_called_once()
    called_contract, called_order = ib.placeOrder.call_args[0]
    assert called_contract is contract
    assert called_order.action == "BUY"
    assert called_order.totalQuantity == 1


@pytest.mark.asyncio
async def test_place_market_order_sell_success():
    ib = Mock()
    contract = Mock()
    expected_trade = Mock()
    ib.placeOrder.return_value = expected_trade

    result = await place_market_order(ib, contract, "SELL", 2)

    assert result is expected_trade
    ib.placeOrder.assert_called_once()
    called_contract, called_order = ib.placeOrder.call_args[0]
    assert called_contract is contract
    assert called_order.action == "SELL"
    assert called_order.totalQuantity == 2


@pytest.mark.asyncio
async def test_place_market_order_invalid_action_raises_value_error():
    ib = Mock()
    contract = Mock()

    with pytest.raises(ValueError, match="action must be 'BUY' or 'SELL'"):
        await place_market_order(ib, contract, "HOLD", 1)


@pytest.mark.asyncio
async def test_place_market_order_invalid_quantity_raises_value_error():
    ib = Mock()
    contract = Mock()

    with pytest.raises(ValueError, match="quantity must be greater than 0"):
        await place_market_order(ib, contract, "BUY", 0)