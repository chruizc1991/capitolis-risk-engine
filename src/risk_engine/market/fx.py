"""
USDJPY FX spot and forward curve — fetch/clean/cache.

Needed only for the JPY compo trades (EQTRS_0005, EQTRS_0006). See
data/MARKET_DATA.md §3. Spot is live via yfinance (`JPY=X`, quoted JPY per
USD, matching the pricer's convention). Forward points still need a real
source (bank/Bloomberg FX swap points) -- not free on yfinance -- so
`fetch_forward_points`/`build_fx_curve` stay stubbed until that's confirmed.
Only the spot is required to *price*; the forward curve is a simulation-only
input (see capitolis_pricers README §6-7).
"""
import yfinance as yf

TICKER = "JPY=X"  # USDJPY: JPY per USD


def fetch_spot():
    """Pull live USDJPY spot. Returns float (JPY per USD)."""
    return yf.Ticker(TICKER).fast_info.last_price


def fetch_forward_points(ref_date):
    """Pull FX swap points across tenors (SPOT, O/N, T/N, 1W...2Y). Not implemented yet."""
    raise NotImplementedError("no free source for FX forward points -- confirm access (data/MARKET_DATA.md #3)")


def build_fx_curve(ref_date, usd_curve, jpy_curve=None):
    """Return a capitolis_pricers.curves.FxCurve from spot + forward points."""
    raise NotImplementedError


def fetch_history(start, end):
    """Daily USDJPY close history for vol/correlation calibration (data/MARKET_DATA.md #5)."""
    return yf.Ticker(TICKER).history(start=start, end=end)["Close"]
