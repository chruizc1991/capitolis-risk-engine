"""
Price the full 16-trade book using REAL market data (as of the run date):
  - USD discount curve: bootstrapped from live Databento SOFR futures
  - Equity spots + dividend yields: live via yfinance, all 37 ISINs
  - USDJPY spot: live via yfinance

This replaces both the illustrative sample_market() (3 spots) and the
scripts/demo_full_book_pricing.py placeholder (basis-as-spot) -- every
number here is a genuine market snapshot.

    python scripts/price_full_book_real_data.py
"""
import csv
import json
import os
from datetime import date

from capitolis_pricers.curves import FxCurve
from capitolis_pricers.market import MarketState
from capitolis_pricers.underlyings_loader import load_equities, load_bonds
from capitolis_pricers.trade_loader import (
    load_equity_trs, load_bond_forward, load_bond_trs)

from risk_engine.market.sofr import fetch_raw as fetch_sofr_raw, build_curve
from risk_engine.market.equities import fetch_raw as fetch_equity_raw, clean as clean_equities
from risk_engine.market.fx import fetch_spot as fetch_fx_spot

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TD = os.path.join(ROOT, "trade_data")
U = os.path.join(TD, "underlyings")


def _isin_to_ticker():
    mapping = {}
    with open(os.path.join(U, "equities.csv"), newline="") as f:
        for row in csv.DictReader(f):
            if row["isin"]:
                mapping[row["isin"]] = row["ticker"]
    return mapping


DEFAULT_CURVE_DATE = date(2026, 8, 28)  # Databento plan has a data lag; today's
                                         # date isn't licensed yet -- see README note


def build_real_market(ref_date=None):
    ref_date = ref_date or DEFAULT_CURVE_DATE
    print(f"Building real MarketState as of {ref_date}...")

    print("  fetching USD SOFR curve (Databento)...")
    sofr_raw = fetch_sofr_raw(ref_date)
    usd = build_curve(ref_date, raw_df=sofr_raw)

    print("  fetching equity spots + dividends (yfinance, 37 names)...")
    isin_to_ticker = _isin_to_ticker()
    eq_raw = fetch_equity_raw(isin_to_ticker)
    eq_clean = clean_equities(eq_raw)
    missing = set(isin_to_ticker) - set(eq_clean)
    if missing:
        print(f"  WARN: no spot for {len(missing)} names: "
              f"{[(isin, isin_to_ticker[isin]) for isin in missing]}")
    spots = {isin: spot for isin, (spot, _) in eq_clean.items()}
    divs = {isin: div for isin, (_, div) in eq_clean.items()}

    print("  fetching USDJPY spot (yfinance)...")
    usdjpy = fetch_fx_spot()
    fx = FxCurve("USD", "JPY", usdjpy, usd)

    return MarketState(
        ref_date=ref_date, reporting_ccy="USD",
        discount_curves={"USD": usd},
        equity_spots=spots,
        equity_dividend_rates=divs,
        fx_curves={("USD", "JPY"): fx},
    ), missing


def main():
    market, missing = build_real_market()

    baskets = load_equities(os.path.join(U, "equities.csv"))
    bonds = load_bonds(os.path.join(U, "bonds.csv"))
    trades = {}
    trades.update(load_equity_trs(os.path.join(TD, "equity_trs.csv"), baskets))
    trades.update(load_bond_forward(os.path.join(TD, "bond_forward.csv"), bonds))
    trades.update(load_bond_trs(os.path.join(TD, "bond_trs.csv"), bonds))

    print(f"\nPricing off REAL market data, ref {market.ref_date}\n")
    results = {}
    for tid, p in trades.items():
        try:
            npv = p.npv(market, reporting=True)
            results[tid] = npv
            print(f"{tid:12s} NPV = {npv:15,.2f} USD")
        except KeyError as exc:
            print(f"{tid:12s} SKIPPED -- {exc}")

    total = sum(results.values())
    print(f"\n{'TOTAL':12s} NPV = {total:15,.2f} USD  ({len(results)}/{len(trades)} trades priced)")

    out_path = os.path.join(ROOT, "data", "processed", f"npv_{market.ref_date}.json")
    with open(out_path, "w") as f:
        json.dump({"ref_date": str(market.ref_date), "npv_by_trade": results,
                   "total_npv": total, "missing_equity_spots": sorted(missing)}, f, indent=2)
    print(f"\nSaved results to {out_path}")


if __name__ == "__main__":
    main()
