"""
Regression test for the SR3 contract -> curve pillar mapping bug found via
the Treasury-yield cross-check (data/MARKET_DATA.md #1): a recently-expired
serial contract must resolve to its own (past) IMM date, not get wrapped a
decade forward -- wrapping silently created a multi-year gap in the curve.

No network access needed -- exercises _contract_period() directly.
"""
from datetime import date

from risk_engine.market.sofr import _contract_period


def test_expired_serial_contract_resolves_to_its_own_decade():
    # ref_date is after SR3Q6's (Aug 2026) IMM date -- it must NOT wrap to 2036.
    ref = date(2026, 8, 28)
    start, end = _contract_period("SR3Q6", ref)
    assert start.year == 2026
    assert start.month == 8
    assert end.year == 2026

    # A contract further out in the same decade should resolve normally too.
    start2, end2 = _contract_period("SR3Z6", ref)
    assert start2.year == 2026
    assert start2.month == 12


def test_no_gap_between_consecutive_quarterly_contracts():
    ref = date(2026, 8, 28)
    _, end_u2 = _contract_period("SR3U2", ref)
    start_z2, _ = _contract_period("SR3Z2", ref)
    gap_days = (start_z2 - end_u2).days
    assert abs(gap_days) <= 1, f"unexpected gap of {gap_days} days between consecutive quarterly contracts"
