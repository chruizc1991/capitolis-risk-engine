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
from datetime import date, timedelta

import databento as db

DATASET = "GLBX.MDP3"        # CME Globex MDP 3.0
SR3_PARENT = "SR3.FUT"       # 3-month SOFR futures, all live contracts
SR1_PARENT = "SR1.FUT"       # 1-month SOFR futures

# Outright futures only, e.g. "SR3Z6" (product + month code + 1-digit year).
# The "parent" symbology also returns spreads/butterflies (e.g. "SR3Z6-SR3U0",
# "SR3:AB 03Y U6") which must be filtered out before use as curve pillars.
_OUTRIGHT_RE = re.compile(r"^(SR3|SR1)[FGHJKMNQUVXZ]\d$")


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


def build_curve(ref_date):
    """Bootstrap a capitolis_pricers.curves.Curve from SR3 futures. Not implemented
    yet -- needs contract-to-tenor mapping (each SR3 contract covers a specific
    3-month IMM period) before the implied rates can be placed on curve pillars."""
    raise NotImplementedError(
        "fetch_raw()/clean() work; still need to map each SR3 contract's IMM "
        "period to a curve pillar (years from ref_date) before bootstrapping "
        "discount factors -- next step once real data has been pulled once"
    )
