"""
USD OIS (SOFR) discount curve — fetch/clean/cache.

Pillars and conventions: data/MARKET_DATA.md §1 (O/N, T/N, 1W...10Y, ACT/360).

Databento does not publish a ready-made SOFR/OIS swap curve -- it only has
the underlying futures. So this builds the curve ourselves from CME SOFR
futures settlement prices (SR3 = 3-month SOFR futures, the standard curve-
building instrument; SR1 = 1-month, useful for the very short end):

    futures price -> implied forward rate -> discount factor per pillar

Requires a Databento API key in the DATABENTO_API_KEY environment variable
(never hardcode it here or pass it in chat/logs). Get one from
https://databento.com -- this project uses paid access already provisioned.
"""
import os
import re
from calendar import monthrange
from datetime import date, timedelta

import databento as db

from capitolis_pricers.curves import Curve
from capitolis_pricers.daycount import add_months, year_fraction

DATASET = "GLBX.MDP3"        # CME Globex MDP 3.0
SR3_PARENT = "SR3.FUT"       # 3-month SOFR futures, all live contracts
SR1_PARENT = "SR1.FUT"       # 1-month SOFR futures

# Outright futures only, e.g. "SR3Z6" (product + month code + 1-digit year).
# The "parent" symbology also returns spreads/butterflies (e.g. "SR3Z6-SR3U0",
# "SR3:AB 03Y U6") which must be filtered out before use as curve pillars.
_OUTRIGHT_RE = re.compile(r"^(SR3|SR1)[FGHJKMNQUVXZ]\d$")

# Standard futures month codes -> calendar month number.
_MONTH_CODE = {"F": 1, "G": 2, "H": 3, "J": 4, "K": 5, "M": 6,
               "N": 7, "Q": 8, "U": 9, "V": 10, "X": 11, "Z": 12}


def _client():
    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        raise RuntimeError(
            "DATABENTO_API_KEY not set. Set it as an environment variable "
            "(e.g. `setx DATABENTO_API_KEY ...` on Windows, then restart the "
            "shell) -- never pass the key inline in code or chat."
        )
    return db.Historical(key=key)


def fetch_raw(ref_date, parent=SR3_PARENT, lookback_days=5):
    """Pull the most recent daily settlement (close) price for every live
    outright SR3 (or SR1) contract as of `ref_date` (spreads/butterflies
    filtered out).

    Returns a pandas DataFrame with one row per contract: symbol,
    close (settlement price), ts_event.
    """
    client = _client()
    end = ref_date if isinstance(ref_date, date) else date.fromisoformat(str(ref_date))
    start = end - timedelta(days=lookback_days)
    data = client.timeseries.get_range(
        dataset=DATASET,
        symbols=[parent],
        stype_in="parent",
        schema="ohlcv-1d",
        start=start.isoformat(),
        end=(end + timedelta(days=1)).isoformat(),
    )
    df = data.to_df().reset_index()   # ts_event is the index in the raw response
    if df.empty:
        raise ValueError(f"No {parent} data returned for {start}..{end}")
    df = df[df["symbol"].apply(lambda s: bool(_OUTRIGHT_RE.match(s)))]
    if df.empty:
        raise ValueError(f"No outright contracts matched for {parent} in {start}..{end}")
    # keep the latest bar per contract
    df = df.sort_values("ts_event").groupby("symbol", as_index=False).last()
    return df[["symbol", "close", "ts_event"]]


def clean(raw_df):
    """Convert SOFR futures settlement prices into (contract, implied_rate) pairs.
    CME rate futures quote as `100 - rate`, so rate = 100 - settlement_price
    (as a percentage; divide by 100 for a decimal rate)."""
    out = []
    for _, row in raw_df.iterrows():
        implied_rate = (100.0 - row["close"]) / 100.0
        out.append({"symbol": row["symbol"], "implied_rate": implied_rate,
                     "ts_event": row["ts_event"]})
    return out


def _third_wednesday(year, month):
    """CME IMM date: the third Wednesday of the month."""
    first_weekday, _ = monthrange(year, month)  # first_weekday: Mon=0..Sun=6
    first_wednesday_day = 1 + (2 - first_weekday) % 7
    return date(year, month, first_wednesday_day + 14)


def _contract_period(symbol, ref_date):
    """Map an outright symbol (e.g. 'SR3Z6') to its 3-month reference period
    (start, end), both `date`s. Period runs IMM-date to IMM-date + 3 months.

    The year code is a single digit (last digit of the year), resolved to
    `ref_date`'s own decade. A contract whose resulting IMM date has already
    passed relative to `ref_date` is a recently-expired one still lingering
    in the feed, not a contract 10 years out -- build_curve() filters those
    out via its "already covered" check rather than us guessing a wrapped
    decade here (an earlier version did that and produced a spurious
    multi-year gap in the curve; see week1 notes)."""
    if not _OUTRIGHT_RE.match(symbol):
        raise ValueError(f"Not an outright SR3/SR1 symbol: {symbol!r}")
    month = _MONTH_CODE[symbol[3]]
    year_digit = int(symbol[4])
    year = ref_date.year - (ref_date.year % 10) + year_digit
    start = _third_wednesday(year, month)
    end = add_months(start, 3)
    return start, end


def build_curve(ref_date, raw_df=None, basis="ACT/365F"):
    """Bootstrap a capitolis_pricers.curves.Curve from SR3 futures.

    Each contract's implied rate is treated as the (simply-compounded, ACT/360)
    forward SOFR rate over its own 3-month reference period. Discount factors
    are chained sequentially from `ref_date` through each period in turn; any
    gap between `ref_date` and the first contract's start is back-filled flat
    at that first contract's rate. This is a reasonable, standard first-pass
    bootstrap -- not a full OIS-convexity-adjusted curve (a refinement for
    later, not needed to unblock pricing).
    """
    ref_date = ref_date if isinstance(ref_date, date) else date.fromisoformat(str(ref_date))
    if raw_df is None:
        raw_df = fetch_raw(ref_date)
    cleaned = clean(raw_df)

    periods = []
    for row in cleaned:
        start, end = _contract_period(row["symbol"], ref_date)
        periods.append((start, end, row["implied_rate"]))
    periods.sort(key=lambda p: p[0])

    pillar_times, discount_factors = [0.0], [1.0]
    df = 1.0
    prev_end = ref_date
    for start, end, rate in periods:
        if end <= prev_end:
            continue  # already covered / stale contract, skip
        tau = year_fraction(prev_end, end, "ACT/360")
        df = df / (1.0 + rate * tau)               # simply-compounded SOFR convention
        pillar_times.append(year_fraction(ref_date, end, basis))
        discount_factors.append(df)
        prev_end = end

    return Curve(ref_date, pillar_times, discount_factors, basis)
