from __future__ import annotations

from ib_insync import IB


async def get_portfolio_summary(ib: IB) -> dict:
    summary = {
        "NetLiquidation": 0.0,
        "AvailableFunds": 0.0,
        "UnrealizedPnL": 0.0,
        "RealizedPnL": 0.0,
    }

    for account_value in ib.accountValues():
        if account_value.tag in summary:
            try:
                summary[account_value.tag] = float(account_value.value)
            except (TypeError, ValueError):
                summary[account_value.tag] = 0.0

    return summary