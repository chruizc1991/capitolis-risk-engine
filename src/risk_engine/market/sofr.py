"""
USD OIS (SOFR) discount curve — fetch/clean/cache.

Pillars and conventions: data/MARKET_DATA.md §1 (O/N, T/N, 1W...10Y, ACT/360).
Stubbed until real data access (FRED for the short end; OIS swap pillar
source TBD) is confirmed.
"""


def fetch_raw(ref_date):
    """Pull raw SOFR/OIS quotes as of `ref_date`. Not implemented yet."""
    raise NotImplementedError("confirm data source before implementing (see data/MARKET_DATA.md #1)")


def clean(raw):
    """Normalize raw quotes into (tenor, rate, day_count) pillar rows."""
    raise NotImplementedError


def build_curve(ref_date):
    """Return a capitolis_pricers.curves.Curve built from cleaned pillars."""
    raise NotImplementedError
