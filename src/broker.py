"""Helpers for placing orders through Interactive Brokers.

This module keeps the order-placement logic small and reusable.
"""

from __future__ import annotations

from ib_insync import Contract, IB, MarketOrder, Trade


def place_market_order(
	ib: IB,
	contract: Contract,
	action: str,
	quantity: float,
) -> Trade:
	"""Place a market order and return the resulting trade.

	Args:
		ib: An active ``ib_insync.IB`` connection.
		contract: The IB contract to trade.
		action: ``BUY`` or ``SELL``.
		quantity: Number of shares or contracts to trade.

	Returns:
		The ``ib_insync.Trade`` returned by ``IB.placeOrder``.
	"""

	normalized_action = action.strip().upper()
	if normalized_action not in {"BUY", "SELL"}:
		raise ValueError("action must be 'BUY' or 'SELL'")

	if quantity <= 0:
		raise ValueError("quantity must be greater than 0")

	order = MarketOrder(normalized_action, quantity)
	return ib.placeOrder(contract, order)
