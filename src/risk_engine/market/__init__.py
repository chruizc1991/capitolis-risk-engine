"""
Market data construction: fetch/clean/cache functions per source, and the
builders that assemble a `capitolis_pricers.market.MarketState` (and its
simulation inputs — curve pillars, dividend rates, FX forwards, vols,
correlations) from collected market data.

Modules are split one-per-source (e.g. `sofr.py` for FRED SOFR/OIS,
`equities.py` for yfinance spots/dividends, `fx.py` for USDJPY) so each
source's fetch/clean/cache steps stay independently testable.
"""
