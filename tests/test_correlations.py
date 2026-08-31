"""
Sanity checks for the correlation matrix builder. Uses small synthetic
series (no network) -- real-data validation results are recorded in
data/MARKET_DATA.md #5.
"""
import numpy as np
import pandas as pd

from risk_engine.market.correlations import (
    build_correlation_matrix, build_returns_table, is_positive_semidefinite)


def _synthetic_data(n=200, seed=0):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    # two correlated equities + one independent one, plus FX and a rate series
    common = rng.normal(size=n)
    eq_a = 100 * np.exp(np.cumsum(0.6 * common + 0.4 * rng.normal(size=n)) * 0.01)
    eq_b = 100 * np.exp(np.cumsum(0.6 * common + 0.4 * rng.normal(size=n)) * 0.01)
    eq_c = 100 * np.exp(np.cumsum(rng.normal(size=n)) * 0.01)
    equities = pd.DataFrame({"EQ_A": eq_a, "EQ_B": eq_b, "EQ_C": eq_c}, index=dates)
    fx = pd.Series(150 * np.exp(np.cumsum(rng.normal(size=n)) * 0.005), index=dates)
    rate = pd.Series(0.04 + np.cumsum(rng.normal(size=n)) * 0.0002, index=dates)
    return equities, fx, rate


def test_correlation_matrix_is_psd():
    equities, fx, rate = _synthetic_data()
    corr = build_correlation_matrix(equities, fx, rate)
    ok, min_eig = is_positive_semidefinite(corr)
    assert ok, f"correlation matrix not PSD, min eigenvalue {min_eig}"


def test_diagonal_is_one():
    equities, fx, rate = _synthetic_data()
    corr = build_correlation_matrix(equities, fx, rate)
    assert np.allclose(np.diag(corr.values), 1.0)


def test_correlated_names_show_higher_correlation_than_independent_one():
    equities, fx, rate = _synthetic_data()
    corr = build_correlation_matrix(equities, fx, rate)
    # EQ_A and EQ_B share a common driver by construction; EQ_C doesn't.
    assert corr.loc["EQ_A", "EQ_B"] > corr.loc["EQ_A", "EQ_C"]


def test_returns_table_drops_incomplete_rows():
    equities, fx, rate = _synthetic_data()
    equities = equities.copy()
    equities.iloc[5, 0] = float("nan")  # inject one gap
    returns = build_returns_table(equities, fx, rate)
    assert not returns.isna().any().any()
