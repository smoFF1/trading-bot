from __future__ import annotations

from ib_insync import IB


async def check_trade_viability(
	ib: IB,
	symbol: str,
	action: str,
	price: float,
	requested_quantity: int = 1,
) -> dict:
	normalized_action = action.strip().upper()
	available_cash = 0.0
	current_position = 0

	for account_value in ib.accountValues():
		if account_value.tag == "AvailableFunds" and account_value.currency == "USD":
			try:
				available_cash = float(account_value.value)
			except (TypeError, ValueError):
				available_cash = 0.0
			break

	for position in ib.positions():
		if position.contract.symbol == symbol:
			try:
				current_position = int(position.position)
			except (TypeError, ValueError):
				current_position = 0
			break

	if requested_quantity <= 0:
		return {
			"approved": False,
			"quantity": requested_quantity,
			"reason": "Requested quantity must be greater than 0.",
		}

	if normalized_action == "BUY":
		required_cash = price * requested_quantity
		if required_cash < available_cash:
			return {
				"approved": True,
				"quantity": requested_quantity,
				"reason": f"Approved: ${required_cash:.2f} required, ${available_cash:.2f} available.",
			}
		return {
			"approved": False,
			"quantity": requested_quantity,
			"reason": f"Rejected: ${required_cash:.2f} required, ${available_cash:.2f} available.",
		}

	if normalized_action == "SELL":
		if current_position >= requested_quantity:
			return {
				"approved": True,
				"quantity": requested_quantity,
				"reason": f"Approved: position of {current_position} covers requested sell of {requested_quantity}.",
			}
		return {
			"approved": False,
			"quantity": requested_quantity,
			"reason": f"Rejected: position of {current_position} is below requested sell of {requested_quantity}.",
		}

	return {
		"approved": False,
		"quantity": requested_quantity,
		"reason": "Unsupported action. Use BUY or SELL.",
	}