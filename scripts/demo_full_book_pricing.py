"""
DEMO ONLY — NOT REAL PRICING.

Extends capitolis_pricers/data/sample_market.py's illustrative MarketState
with PLACEHOLDER spots for all 41 real underlying names (using each name's
`basis` from trade_data/underlyings/equities.csv as a stand-in spot, since no
real market data has been collected yet — see data/MARKET_DATA.md) so all 16
trades in the book can run through the pricer end-to-end.

Purpose: prove the full pipeline (trade loaders -> pricers -> NPV) works
mechanically across every trade type, ahead of real market data being ready.
The dollar figures below are NOT meaningful — they use fake spot prices.

    python scripts/demo_full_book_pricing.py
"""
import csv
import os

from capitolis_pricers.curves import flat_curve, FxCurve
from capitolis_pricers.market import MarketState
from capitolis_pricers.underlyings_loader import load_equities, load_bonds
from capitolis_pricers.trade_loader import (
    load_equity_trs, load_bond_forward, load_bond_trs)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TD = os.path.join(ROOT, "trade_data")
U = os.path.join(TD, "underlyings")
REF_DATE = "2026-01-15"


def _placeholder_spots():
    """Placeholder spot per ISIN = that name's `basis` (its own currency).
    Stand-in only until real spots are collected (data/MARKET_DATA.md #2)."""
    spots = {}
    with open(os.path.join(U, "equities.csv"), newline="") as f:
        for row in csv.DictReader(f):
            isin, basis = row["isin"], row["basis"]
            if isin and basis:
                spots[isin] = float(basis)
    return spots


def demo_market():
    usd = flat_curve(REF_DATE, 0.04)
    fx = FxCurve("USD", "JPY", 150.0, usd)
    spots = _placeholder_spots()
    return MarketState(
        ref_date=REF_DATE, reporting_ccy="USD",
        discount_curves={"USD": usd},
        equity_spots=spots,
        equity_dividend_rates={isin: 0.02 for isin in spots},
        fx_curves={("USD", "JPY"): fx},
    )


def main():
    market = demo_market()
    baskets = load_equities(os.path.join(U, "equities.csv"))
    bonds = load_bonds(os.path.join(U, "bonds.csv"))

    trades = {}
    trades.update(load_equity_trs(os.path.join(TD, "equity_trs.csv"), baskets))
    trades.update(load_bond_forward(os.path.join(TD, "bond_forward.csv"), bonds))
    trades.update(load_bond_trs(os.path.join(TD, "bond_trs.csv"), bonds))

    print("DEMO - placeholder market data, NOT real prices\n")
    print(f"Valuation {market.ref_date}   reporting {market.reporting_ccy}\n")
    for tid, p in trades.items():
        print(f"{tid:12s} NPV = {p.npv(market, reporting=True):15,.2f} {market.reporting_ccy}")


if __name__ == "__main__":
    main()
