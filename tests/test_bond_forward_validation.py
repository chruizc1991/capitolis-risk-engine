"""
Validation sanity check: price a single risk-free bond forward using only the
USD curve, cross-check the pricer's forward clean price against an
independent closed-form calculation, and confirm the NPV sign is directionally
correct. This is the cleanest benchmark before layering in equity/FX
complexity (see src/risk_engine/validation/).
"""
import math

from capitolis_pricers.bond import FixedRateBond
from capitolis_pricers.curves import flat_curve
from capitolis_pricers.market import MarketState
from capitolis_pricers.pricers.bond_forward import BondForwardTrade

REF_DATE = "2026-01-15"
FLAT_RATE = 0.04


def _market():
    return MarketState(
        ref_date=REF_DATE,
        discount_curves={"USD": flat_curve(REF_DATE, FLAT_RATE)},
    )


def _bond():
    # Treasury-like bond, semiannual 30/360 coupons, well past its first coupon.
    return FixedRateBond(
        issue_date="2024-06-15", maturity_date="2034-06-15",
        coupon=0.04, frequency_months=6, day_count="30/360",
    )


def _closed_form_forward_clean(bond, curve, forward_date):
    """Independent recomputation: forward dirty = PV(remaining CFs) / DF(T)."""
    T = forward_date
    df_T = curve.discount(T)
    pv = sum(amt * curve.discount(pay) for pay, amt in bond.cashflows() if pay > T)
    forward_dirty = pv / df_T
    return forward_dirty - bond.accrued(T)


def test_forward_clean_matches_closed_form():
    market = _market()
    curve = market.discount("USD")
    bond = _bond()
    forward_date = "2027-01-15"

    trade = BondForwardTrade(bond, forward_date=forward_date, strike_clean=100.0,
                              position="long", notional=10_000_000)

    expected = _closed_form_forward_clean(bond, curve, trade.forward_date)
    actual = trade.forward_clean_price(market)
    assert math.isclose(actual, expected, rel_tol=1e-9)


def test_long_forward_is_directionally_sane():
    market = _market()
    bond = _bond()
    forward_date = "2027-01-15"

    # Struck well below fair value -> long forward should be in-the-money (+NPV).
    cheap = BondForwardTrade(bond, forward_date, strike_clean=80.0,
                              position="long", notional=10_000_000)
    assert cheap.npv(market) > 0

    # Struck well above fair value -> long forward should be out-of-the-money (-NPV).
    rich = BondForwardTrade(bond, forward_date, strike_clean=120.0,
                             position="long", notional=10_000_000)
    assert rich.npv(market) < 0

    # Long and short at the same strike are exact mirror images.
    short = BondForwardTrade(bond, forward_date, strike_clean=80.0,
                              position="short", notional=10_000_000)
    assert math.isclose(cheap.npv(market), -short.npv(market), rel_tol=1e-12)
