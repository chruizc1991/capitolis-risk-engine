"""
Pairwise correlation matrix across all risk factors (data/MARKET_DATA.md #5) --
the historical-proxy correlation build, computed from the 3yr daily history
already pulled (pull_historical_data.py) and the per-factor return convention
already established in vols.py (log returns for equity/FX, simple differences
for the rate level).

Uses only rows where ALL factors have data (pairwise-complete correlation can
produce a non-positive-semidefinite matrix when missingness differs across
series -- inner-joining on common dates avoids that by construction).
"""
import numpy as np
import pandas as pd


def build_returns_table(equity_history_df, fx_series, sofr_series):
    """One column per factor, log returns for equity/FX and simple
    differences for the rate, aligned on dates where all factors have data."""
    equity_returns = np.log(equity_history_df / equity_history_df.shift(1))
    fx_returns = np.log(fx_series / fx_series.shift(1)).rename("FX_USDJPY")
    rate_changes = sofr_series.diff().rename("RATE_USD")

    combined = equity_returns.join(fx_returns, how="inner").join(rate_changes, how="inner")
    return combined.dropna(how="any")


def build_correlation_matrix(equity_history_df, fx_series, sofr_series):
    """Pairwise correlation matrix (pandas DataFrame) across all factors."""
    returns = build_returns_table(equity_history_df, fx_series, sofr_series)
    return returns.corr()


def is_positive_semidefinite(corr_matrix, tol=1e-8):
    """Sanity check: a valid correlation matrix for joint simulation must be
    PSD (no negative eigenvalues beyond numerical noise)."""
    eigenvalues = np.linalg.eigvalsh(corr_matrix.values)
    return bool(eigenvalues.min() >= -tol), float(eigenvalues.min())
