"""
Volatilities per risk factor (data/MARKET_DATA.md #5) — computed as historical
realized vol from the 3yr daily history already pulled (scripts/pull_historical_data.py),
since we don't have an implied-vol (options) source. This is exactly the
documented fallback: "Source it as you like (implied, put-call parity)" for
equities in the pricer contract, and the market data spec explicitly allows a
historical proxy.

Equity / FX: lognormal vol on daily log returns, annualized (sqrt(252)).
Rate: normal vol on daily rate changes (rates can be small/negative near
zero, so log returns aren't meaningful), annualized the same way.

None of this is used by the linear pricers -- it's a simulation-only input
(models/, not implemented yet).
"""
import numpy as np
import pandas as pd

TRADING_DAYS = 252


def equity_vol(price_series):
    """Annualized lognormal realized vol from a price series (pandas Series)."""
    log_ret = np.log(price_series / price_series.shift(1)).dropna()
    return float(log_ret.std() * np.sqrt(TRADING_DAYS))


def fx_vol(price_series):
    """Same lognormal realized-vol calc as equity_vol -- FX behaves the same way."""
    return equity_vol(price_series)


def rate_vol(rate_level_series):
    """Annualized normal (absolute) vol from a rate LEVEL series (decimal,
    e.g. 0.04 = 4%). Uses simple differences, not log returns -- log returns
    are meaningless/undefined when rates are near zero or negative."""
    diffs = rate_level_series.diff().dropna()
    return float(diffs.std() * np.sqrt(TRADING_DAYS))


def build_vol_table(equity_history_df, fx_series, sofr_series):
    """Assemble the full vol table: one row per factor, matching
    data/MARKET_DATA.md #5's schema (factor, type, tenor, volatility).
    `tenor` is "historical_3y" throughout -- these are realized, not
    tenor-specific implied vols."""
    rows = []
    for isin in equity_history_df.columns:
        v = equity_vol(equity_history_df[isin].dropna())
        rows.append({"factor": isin, "type": "lognormal", "tenor": "historical_3y",
                     "volatility": v})
    rows.append({"factor": "FX_USDJPY", "type": "lognormal", "tenor": "historical_3y",
                 "volatility": fx_vol(fx_series.dropna())})
    rows.append({"factor": "RATE_USD", "type": "normal", "tenor": "historical_3y",
                 "volatility": rate_vol(sofr_series.dropna())})
    return pd.DataFrame(rows)
