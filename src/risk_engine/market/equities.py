"""
Equity spot prices + dividend yields for the 41 underlying names — fetch/clean/cache.

Keyed by ISIN (see data/MARKET_DATA.md §2); ISIN->ticker mapping comes from
trade_data/underlyings/equities.csv. Stubbed until real data access
(yfinance) is confirmed.
"""


def fetch_raw(isins, ref_date):
    """Pull raw spot + dividend data for the given ISINs as of `ref_date`. Not implemented yet."""
    raise NotImplementedError("confirm data source before implementing (see data/MARKET_DATA.md #2)")


def clean(raw):
    """Normalize into {isin: (spot, dividend_rate)}."""
    raise NotImplementedError


def fetch_history(isins, start, end):
    """Daily return history for vol/correlation calibration (data/MARKET_DATA.md #5)."""
    raise NotImplementedError
