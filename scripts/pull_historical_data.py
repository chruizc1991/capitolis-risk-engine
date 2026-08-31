"""
Pull ~3 years of daily history for every risk factor, for Week 2's
correlation build (data/MARKET_DATA.md #5). Does not compute correlations
itself -- just lands clean daily series in data/processed/ so that work
isn't blocked on data collection.

Risk factors: USD short rate (SOFR level, FRED), all 37 equity spots
(yfinance), USDJPY spot (yfinance).

    python scripts/pull_historical_data.py
"""
import csv
import os
from datetime import date, timedelta

import pandas as pd

from risk_engine.market.sofr import fetch_history as fetch_sofr_history
from risk_engine.market.equities import fetch_history as fetch_equity_history
from risk_engine.market.fx import fetch_history as fetch_fx_history

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TD = os.path.join(ROOT, "trade_data")
U = os.path.join(TD, "underlyings")
OUT = os.path.join(ROOT, "data", "processed")

LOOKBACK_YEARS = 3


def _isin_to_ticker():
    mapping = {}
    with open(os.path.join(U, "equities.csv"), newline="") as f:
        for row in csv.DictReader(f):
            if row["isin"]:
                mapping[row["isin"]] = row["ticker"]
    return mapping


def main():
    end = date.today()
    start = end - timedelta(days=int(LOOKBACK_YEARS * 365.25))
    print(f"Pulling {LOOKBACK_YEARS}yr history: {start} .. {end}\n")

    print("SOFR (rate level, FRED)...")
    sofr = fetch_sofr_history(start, end)
    sofr.to_frame("SOFR").to_csv(os.path.join(OUT, "history_sofr.csv"))
    print(f"  {len(sofr)} daily observations saved")

    print("\nUSDJPY (yfinance)...")
    fx = fetch_fx_history(start, end)
    # Same tz-naive/date-only normalization as equities below -- yfinance
    # returns a tz-aware index that won't align with FRED's tz-naive one.
    fx = fx.tz_localize(None).groupby(fx.tz_localize(None).index.date).last()
    fx.index.name = "date"
    fx.to_frame("USDJPY").to_csv(os.path.join(OUT, "history_usdjpy.csv"))
    print(f"  {len(fx)} daily observations saved")

    print(f"\nEquities ({len(_isin_to_ticker())} names, yfinance)...")
    isin_to_ticker = _isin_to_ticker()
    history = fetch_equity_history(isin_to_ticker, start, end)
    # US and Tokyo names trade on different market hours -> different raw
    # timestamps; normalize to date-only (each exchange's own local trading
    # day) before combining, or the merge is mostly NaN from misalignment.
    ok = {isin: s.tz_localize(None).groupby(s.tz_localize(None).index.date).last()
          for isin, s in history.items() if s is not None and len(s) > 0}
    missing = set(isin_to_ticker) - set(ok)
    combined = pd.DataFrame(ok)
    combined.index.name = "date"
    combined.to_csv(os.path.join(OUT, "history_equities.csv"))
    print(f"  {len(ok)}/{len(isin_to_ticker)} names pulled, {combined.shape[0]} rows")
    if missing:
        print(f"  WARN missing: {[(isin, isin_to_ticker[isin]) for isin in missing]}")

    print(f"\nAll saved to {OUT}")


if __name__ == "__main__":
    main()
