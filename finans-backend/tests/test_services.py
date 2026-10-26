from datetime import date

import pytest

from app.services import LedgerError, Txn, build_installments, check_mutation, ledger_ok, run_fifo


def t(q, p, d, i=None):
    return Txn(q, p, date.fromisoformat(d), i)


def test_fifo_remaining_lots_and_realized():
    lots, realized = run_fifo(
        [t(10, 100, "2026-01-01", 1), t(10, 200, "2026-02-01", 2), t(-15, 300, "2026-03-01", 3)]
    )
    assert [round(l["qty"], 6) for l in lots] == [5.0]
    assert lots[0]["price"] == 200
    # 10 adet (300-100) + 5 adet (300-200)
    assert realized == pytest.approx(10 * 200 + 5 * 100)


def test_sell_before_buy_is_rejected_in_strict_mode():
    ledger = [t(-5, 10, "2026-01-01", 1), t(10, 10, "2026-02-01", 2)]
    with pytest.raises(LedgerError):
        run_fifo(ledger, strict=True)
    assert not ledger_ok(ledger)


def test_same_day_buy_counts_before_sell():
    assert ledger_ok([t(-5, 10, "2026-01-01", 2), t(5, 9, "2026-01-01", 1)])


def test_check_mutation_blocks_new_overdraw_but_not_preexisting_breakage():
    good = [t(10, 1, "2026-01-01", 1)]
    with pytest.raises(LedgerError):
        check_mutation(good, good + [t(-11, 1, "2026-02-01")])
    broken = [t(-1, 1, "2026-01-01", 1)]
    check_mutation(broken, broken + [t(1, 1, "2026-02-01")])  # kilitlenmemeli


def test_installments_interest_free_remainder_on_last():
    plan = build_installments(100.0, 3, 0.0, date(2026, 1, 31))
    assert [a for _, a in plan] == [33.33, 33.33, 33.34]
    assert [d.isoformat() for d, _ in plan] == ["2026-01-31", "2026-02-28", "2026-03-31"]


def test_installments_with_monthly_interest_is_annuity():
    plan = build_installments(100000.0, 12, 3.0, date(2026, 1, 1))
    amount = plan[0][1]
    assert amount == pytest.approx(10046.20, abs=0.01)
    assert len({a for _, a in plan}) == 1
