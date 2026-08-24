# Week 1 — Pricer Contract Review (2026-08-24)

Full source: [`docs/pricer_contract.md`](../pricer_contract.md) (original
`capitolis_pricers/README.md`). This is the working summary of what each
pricer needs from `MarketState` and the conventions our own market data must
match.

## The contract

Every pricer is a pure function of a `MarketState`:

```python
npv = pricer.npv(market)                  # NPV in the trade's own currency
npv = pricer.npv(market, reporting=True)  # NPV converted to market.reporting_ccy
```

To simulate, we build a fresh `MarketState` per (scenario, horizon) node and
call `pricer.npv(node_market)` again — the pricers themselves hold no state
across nodes.

`MarketState` fields (`capitolis_pricers/market.py`):

| Field | Type | Used by |
|---|---|---|
| `ref_date` | date | all — valuation snapshot date |
| `reporting_ccy` | str | `reporting=True` FX conversion |
| `discount_curves` | `{ccy: Curve}` | all — only `"USD"` needed for this book |
| `equity_spots` | `{isin: float}` | Equity TRS |
| `equity_dividend_rates` | `{isin: float}` | not used to price (drift input for simulation only) |
| `fx_curves` | `{(base,quote): FxCurve}` | JPY compo Equity TRS |
| `equity_vols`, `correlations` | engine inputs | not used by the linear pricers at all |
| `credit_curves` | `{issuer: CreditCurve}` | optional risky-bond extension only |

## What each pricer needs

### Equity TRS (`pricers/equity_trs.py`)
- Equity leg: `sum_i shares_i * DF(end) * (F_i(end) - basis_i)`, where
  `F(t) = S_ccy / DF(end)` — a **total-return** forward that grows at the
  risk-free rate `r`. Dividends are 100% pass-through, so `q` (dividend rate)
  is **not** used by the pricer — it only matters for the simulation drift
  `(r - q)`.
- Funding leg: floating (`SOFR_fwd + spread`) unless `fixed_rate` is given.
- Position is shares + basis per name; notional weight is derived, not input.
- **JPY compo (EQTRS_0005, EQTRS_0006):** `trade_ccy = USD` on a JPY-quoted
  position. The pricer converts the JPY spot at FX and grows the USD value on
  the USD curve — there is **no JPY discount curve**, and both legs settle in
  USD. `basis` for a compo name is the locked USD level at inception
  (`S_JPY × FX` at trade date), not a JPY price. This is a 3-risk-factor
  trade: USD curve + equity spot + USDJPY FX (vs. 2 factors — USD curve +
  equity spot — for the 6 USD-quoted Equity TRS).

### Bond Forward (`pricers/bond_forward.py`)
`NPV = sign * (notional/par) * DF(T) * (forward_clean(T) - strike_clean)`.
Forward clean price is either:
- **repo-financed** (`repo_rate` given): spot dirty price carried to `T` at
  the repo rate (ACT/360), less coupons in the window (each carried at repo
  from its pay date), minus accrued at `T`. All 4 of our bond forwards give
  `repo_rate`, so this branch is what's exercised on trade data.
- **curve-derived** (`repo_rate` blank): forward implied purely from the
  discount curve. This is the branch simulation will use at future nodes,
  since a future repo rate can't be pre-observed.

### Bond TRS (`pricers/bond_trs.py`)
Return leg (bond price change + coupons) + funding leg over the reset
schedule, scaled by `notional/par`. Funding is floating or `fixed_rate`,
same convention as Equity TRS. Bonds are risk-free — discounted on the USD
curve; issuer credit is an optional extension (§8 of the contract), not
needed for this book (all 5 bonds are US Treasuries).

## Conventions to match in our own market data

- **Day count:** curve time is ACT/365F; USD money-market/SOFR-OIS quotes are
  ACT/360; bond coupons are 30/360 (all 5 bonds in `bonds.csv` use 30/360).
  Bond forward repo carry uses ACT/360.
- **Curve interpolation:** log-linear on discount factors (equiv.
  piecewise-flat instantaneous forwards) — the `Curve` class in `curves.py`,
  ORE/QuantLib default. Flat zero-rate extrapolation beyond the last pillar.
- **Compounding:** curves are continuously-compounded zero rates internally
  (`zero_curve()` takes continuously-compounded zero rates and exponentiates
  to discount factors).
- **FX quoting convention:** `USDJPY` = JPY per USD (base=USD, quote=JPY,
  spot ≈ 150). `FxCurve.forward()` uses covered interest parity,
  `F(0,T) = S · DF_base(T) / DF_quote(T)`; since there's no JPY curve, our FX
  forward curve is built directly from spot + swap points, not derived from
  two rate curves.
- **Dates:** `MM/DD/YYYY` (US month-first) or ISO `YYYY-MM-DD`, both accepted
  by `daycount.to_date()`.
- **Blank vs. zero:** blank means "use the default" (e.g. floating funding);
  a literal `0` in `fixed_rate` books an actual 0% fixed leg. We must
  preserve this distinction if we ever regenerate/edit trade CSVs.
- **Minimum data to price:** only the USD discount curve, equity spots, and
  the USDJPY FX spot — no vols, no dividend rates, no correlations. Those are
  simulation-only inputs (data/MARKET_DATA.md).

## `price_all.py` run

Ran `python -m capitolis_pricers.examples.price_all` from the repo root
against the sample market shipped in `capitolis_pricers/data/sample_market.py`.
Full traceback: [`price_all_run_log_2026-08-24.txt`](price_all_run_log_2026-08-24.txt).

**Result: fails as expected, not a bug.** `sample_market()` only defines spots
for 3 illustrative securities; the real `trade_data/underlyings/equities.csv`
references 41 distinct ISINs, so the first Equity TRS trade
(`EQTRS_0001`, ISIN `US8168501018`) raises `KeyError: No spot for security`.
The sample market is explicitly illustrative ("students build their own
MarketState from collected data").

**Confirmed working end-to-end:** the 4 Bond Forward and 4 Bond TRS trades,
which need only the USD curve, price cleanly against `sample_market()`:

```
BF_0001      317,422.61      BTRS_0001    133,940.98
BF_0002     -681,169.58      BTRS_0002     25,973.53
BF_0003   88,465,054.80      BTRS_0003      3,698.41
BF_0004    1,872,914.48      BTRS_0004        -38.66
```

Equity TRS pricing (including the JPY compo trades) will run end-to-end once
`data/MARKET_DATA.md` §2/§3 (equity spots, FX spot) are collected.

## Trade inventory (16 trades)

**By instrument type:**

| Instrument | Count |
|---|---|
| Equity TRS | 8 (7 USD, **1 JPY compo**) |
| Bond Forward | 4 |
| Bond TRS | 4 |

Note: `trade_data/underlyings/equities.csv` shows **2** JPY-basket trade IDs
(`EQTRS_0005`, `EQTRS_0006`), not 1. See "JPY compo trades" flag below — this
differs from the brief's "1 JPY compo" count and should be confirmed with
Capitolis at the Friday check-in.

**By counterparty (3 total):**

| Counterparty | Trades |
|---|---|
| `CPTY_A` | EQTRS_0001, EQTRS_0002, EQTRS_0003, BF_0001, BF_0002, BTRS_0001 (6) |
| `CPTY_B` | EQTRS_0004, EQTRS_0005, EQTRS_0006, BTRS_0002, BTRS_0003 (5) |
| `CPTY_C` | EQTRS_0007, EQTRS_0008, BF_0003, BF_0004, BTRS_0004 (5) |

**41 underlying equity names** across the 8 Equity TRS baskets (35 USD-quoted
+ 6 JPY-quoted, spanning EQTRS_0001–0004, 0007–0008 for USD and EQTRS_0005–0006
for JPY). Full basket detail in `trade_data/underlyings/equities.csv`.

**5 bond types** (`Bond_A`–`Bond_E`), all US Treasuries, referenced by the 4
Bond Forwards and 4 Bond TRS (`Bond_B`, `Bond_C`, `Bond_E` each referenced by
two trades).

## ⚠ JPY compo trades — flagged

`EQTRS_0005` and `EQTRS_0006` are JPY-quoted baskets (`currency = JPY` in
`equities.csv`, tickers like `6902.T`). Per the pricer contract §4/§7, a
compo trade has **3 risk factors** instead of 2: **USD curve + equity spot +
USDJPY FX** (vs. USD curve + equity spot only for the other 6). This affects
both the market data we must collect (USDJPY FX curve, §3) and the
correlation matrix (USDJPY must be included as its own factor, §5/§6).

The kickoff brief describes "1 Equity TRS incl. 1 JPY compo" (implying 1 of
the 8 is JPY); the data shows 2 JPY-basket trade IDs out of 8. Flagging this
discrepancy for the Friday check-in rather than silently reconciling it.
