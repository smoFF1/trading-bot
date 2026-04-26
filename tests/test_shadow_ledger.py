import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.shadow_ledger import ShadowLedger, calculate_realistic_commission


def test_calculate_realistic_commission_buy_matches_tiered_formula():
    commission = calculate_realistic_commission("BUY", 10, 100.0)

    assert commission == pytest.approx(0.45076, rel=1e-9)


def test_calculate_realistic_commission_sell_includes_regulatory_fees():
    commission = calculate_realistic_commission("SELL", 10, 100.0)

    assert commission == pytest.approx(0.477133, rel=1e-9)


@pytest.mark.parametrize(
    "action, shares, price, expected_message",
    [
        ("HOLD", 10, 100.0, "action must be 'BUY' or 'SELL'"),
        ("BUY", 0, 100.0, "shares must be greater than 0"),
        ("BUY", -1, 100.0, "shares must be greater than 0"),
        ("BUY", 10, 0.0, "price must be greater than 0"),
        ("BUY", 10, -1.0, "price must be greater than 0"),
    ],
)
def test_calculate_realistic_commission_rejects_invalid_inputs(action, shares, price, expected_message):
    with pytest.raises(ValueError, match=expected_message):
        calculate_realistic_commission(action, shares, price)


def test_record_trade_buy_applies_slippage_and_commission_to_cash():
    ledger = ShadowLedger(initial_cash=1000.0)

    ledger.record_trade("BUY", 5, 100.0)

    expected_commission = calculate_realistic_commission("BUY", 5, 100.0)
    expected_cost = (100.0 + 0.01) * 5
    assert ledger.virtual_cash == pytest.approx(1000.0 - expected_cost - expected_commission, rel=1e-9)
    assert ledger.total_commissions_paid == pytest.approx(expected_commission, rel=1e-9)


def test_record_trade_sell_updates_realized_pnl_and_cash():
    ledger = ShadowLedger(initial_cash=1000.0)
    ledger.record_trade("BUY", 5, 100.0)

    ledger.record_trade("SELL", 2, 101.0)

    assert ledger.realized_pnl > 0
    assert ledger.virtual_cash > 1000.0 - ((100.0 + 0.01) * 5)


def test_record_trade_rejects_selling_more_than_tracked_position():
    ledger = ShadowLedger(initial_cash=1000.0)

    with pytest.raises(ValueError, match="cannot sell more shares"):
        ledger.record_trade("SELL", 1, 100.0)


@pytest.mark.parametrize(
    "action, shares, execution_price, expected_message",
    [
        ("HOLD", 10, 100.0, "action must be 'BUY' or 'SELL'"),
        ("BUY", 0, 100.0, "shares must be greater than 0"),
        ("BUY", -1, 100.0, "shares must be greater than 0"),
        ("BUY", 10, 0.0, "execution_price must be greater than 0"),
        ("BUY", 10, -1.0, "execution_price must be greater than 0"),
    ],
)
def test_record_trade_rejects_invalid_inputs(action, shares, execution_price, expected_message):
    ledger = ShadowLedger(initial_cash=1000.0)

    with pytest.raises(ValueError, match=expected_message):
        ledger.record_trade(action, shares, execution_price)
