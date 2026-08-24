"""
USDJPY FX spot and forward curve — fetch/clean/cache.

Needed only for the JPY compo trades (EQTRS_0005, EQTRS_0006). See
data/MARKET_DATA.md §3. Stubbed until real data access (yfinance for spot;
forward points source TBD) is confirmed.
"""


def fetch_spot(ref_date):
    """Pull USDJPY spot as of `ref_date`. Not implemented yet."""
    raise NotImplementedError("confirm data source before implementing (see data/MARKET_DATA.md #3)")


def fetch_forward_points(ref_date):
    """Pull FX swap points across tenors (SPOT, O/N, T/N, 1W...2Y)."""
    raise NotImplementedError


def build_fx_curve(ref_date, usd_curve, jpy_curve=None):
    """Return a capitolis_pricers.curves.FxCurve from spot + forward points."""
    raise NotImplementedError
