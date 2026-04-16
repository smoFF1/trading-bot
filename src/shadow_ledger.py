from __future__ import annotations


class ShadowLedger:
    def __init__(self, initial_cash: float = 0.0) -> None:
        self.virtual_cash = float(initial_cash)
        self.unrealized_pnl = 0.0
        self.realized_pnl = 0.0
        self.total_commissions_paid = 0.0
        self._position_shares = 0
        self._position_cost = 0.0

    @staticmethod
    def calculate_realistic_commission(action: str, shares: int, price: float) -> float:
        normalized_action = action.strip().upper()
        if normalized_action not in {"BUY", "SELL"}:
            raise ValueError("action must be 'BUY' or 'SELL'")
        if shares <= 0:
            raise ValueError("shares must be greater than 0")
        if price <= 0:
            raise ValueError("price must be greater than 0")

        base = min(max(shares * 0.0035, 0.35), shares * price * 0.01)
        clearing = shares * 0.0002
        exchange_estimation = shares * 0.003
        reg_fees = 0.0
        if normalized_action == "SELL":
            reg_fees = (shares * 0.000175) + (shares * price * 0.0000206)

        total_before_tax = base + clearing + exchange_estimation + reg_fees
        return total_before_tax * 1.18

    def record_trade(self, action: str, shares: int, execution_price: float) -> None:
        normalized_action = action.strip().upper()
        if normalized_action not in {"BUY", "SELL"}:
            raise ValueError("action must be 'BUY' or 'SELL'")
        if shares <= 0:
            raise ValueError("shares must be greater than 0")
        if execution_price <= 0:
            raise ValueError("execution_price must be greater than 0")

        effective_price = execution_price + 0.01 if normalized_action == "BUY" else execution_price - 0.01
        commission = self.calculate_realistic_commission(normalized_action, shares, execution_price)
        self.total_commissions_paid += commission

        if normalized_action == "BUY":
            trade_value = effective_price * shares
            self.virtual_cash -= trade_value + commission
            self._position_cost += trade_value
            self._position_shares += shares
            return

        if shares > self._position_shares:
            raise ValueError("cannot sell more shares than currently tracked in shadow ledger")

        average_cost = self._position_cost / self._position_shares if self._position_shares else 0.0
        cost_basis = average_cost * shares
        proceeds = effective_price * shares
        realized_trade_pnl = proceeds - cost_basis - commission

        self.virtual_cash += proceeds - commission
        self.realized_pnl += realized_trade_pnl
        self._position_shares -= shares
        self._position_cost -= cost_basis


def calculate_realistic_commission(action: str, shares: int, price: float) -> float:
    return ShadowLedger.calculate_realistic_commission(action, shares, price)