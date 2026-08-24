# Capitolis Counterparty Credit Risk Engine

Monte Carlo counterparty credit risk (CCR) engine for Capitolis' ESF
derivatives book — Equity TRS (incl. JPY compo), Bond Forwards, and Bond
TRS — built over a 7-week Berkeley MFE industry project.

## Structure

```
.
├── data/
│   ├── raw/                   # untracked raw pulls (gitignored)
│   ├── processed/             # untracked cleaned/cached data (gitignored)
│   ├── MARKET_DATA.md         # collection checklist: source, status, per series
│   └── MARKET_DATA_source.md  # original field spec (from capitolis_pricers)
├── trade_data/                 # the 16 trades + underlyings (Capitolis-supplied)
├── capitolis_pricers/           # pricing library (Capitolis-supplied, standard-library only)
├── src/risk_engine/
│   ├── market/                 # MarketState construction: fetch/clean/cache per source
│   ├── models/                 # stochastic risk factor models (scaffolding — Week 2+)
│   ├── simulation/             # Monte Carlo engine (scaffolding — Week 2+)
│   ├── exposure/                # EE/PFE/MPE aggregation (scaffolding — Week 3+)
│   └── validation/              # analytical benchmarks (e.g. bond forward closed form)
├── notebooks/                   # exploration notebooks
├── tests/                       # validation + unit tests
└── docs/
    ├── kickoff_deck.pdf
    ├── pricer_contract.md       # original capitolis_pricers/README.md
    └── week_notes/               # dated per-week check-in notes
```

## Install

```bash
pip install -r requirements.txt
```

or, with the package layout:

```bash
pip install -e .
```

## Run

Price the sample trades against the pricer library's illustrative sample
market (only the 4 Bond Forward / Bond TRS trades succeed until real equity
spot data is loaded — see Week 1 status below):

```bash
python -m capitolis_pricers.examples.price_all
```

Run tests:

```bash
pip install pytest
pytest tests/
```

## Week 1 status (2026-08-24)

**Done:**
- Explored `capitolis_pricers/` and read the full pricer contract
  ([`docs/pricer_contract.md`](docs/pricer_contract.md)); summarized field
  contracts and conventions in
  [`docs/week_notes/week1_pricer_review.md`](docs/week_notes/week1_pricer_review.md).
- Repo reorganized into the structure above; flattened the doubled
  `capitolis_pricers/capitolis_pricers/` nesting from the original zip.
- Ran `price_all.py` end-to-end for the 4 Bond Forward + 4 Bond TRS trades
  (succeeds against the sample market — only needs the USD curve). The 8
  Equity TRS trades fail against the sample market by design (it only ships
  3 illustrative spots, not the 41 real ISINs) — expected, not a bug. Full
  log: [`docs/week_notes/price_all_run_log_2026-08-24.txt`](docs/week_notes/price_all_run_log_2026-08-24.txt).
- Inventoried all 16 trades by instrument type and counterparty, listed the
  41 underlying equity names and 5 bond types, and flagged a discrepancy: the
  data shows **2** JPY-compo Equity TRS trades (`EQTRS_0005`, `EQTRS_0006`),
  not the 1 described in the kickoff brief — needs confirming with Capitolis.
- Built [`data/MARKET_DATA.md`](data/MARKET_DATA.md), a per-series checklist
  (source, identifier, date range, frequency, status) for all required market
  data, reconciled against the pricer package's own spec.
- Set up `src/risk_engine/market/` with fetch/clean/cache stubs split one
  module per source (`sofr.py`, `equities.py`, `fx.py`, `state.py`) — logic
  intentionally not implemented until real data access is confirmed.
- Wrote a validation sanity test
  ([`tests/test_bond_forward_validation.py`](tests/test_bond_forward_validation.py))
  pricing a risk-free bond forward off a flat USD curve, cross-checked
  against an independent closed-form recomputation, plus directional
  (ITM/OTM/long-short-symmetry) checks. Passes.
- `models/`, `simulation/`, `exposure/` scaffolded with `__init__.py` +
  docstrings only — no modeling logic yet, per scope.

**Open / blocked:**
- **No real market data pulled yet.** Blocked on confirming access to a
  paid OIS swap curve source (FRED alone gives spot SOFR, not full pillars)
  and FX forward points beyond spot — flagging for Friday's check-in.
- Equity spot/dividend collection (41 names) and USDJPY FX not started —
  stubbed in `src/risk_engine/market/equities.py` and `fx.py`, pending the
  above data-access decision (planned: yfinance).
- Historical return series (1-3yr, all 43 risk factors) for the Week 2
  correlation build not started — should begin once data access is settled,
  since Week 2 depends on it.
- JPY compo trade count discrepancy (2 vs. brief's 1) needs Capitolis
  confirmation.

## Trades at a glance

| Instrument | Count | Counterparties |
|---|---|---|
| Equity TRS (incl. 2 JPY compo) | 8 | CPTY_A, CPTY_B, CPTY_C |
| Bond Forward | 4 | CPTY_A, CPTY_C |
| Bond TRS | 4 | CPTY_A, CPTY_B, CPTY_C |

41 underlying equity names, 5 bond types (all US Treasuries). Full detail in
[`docs/week_notes/week1_pricer_review.md`](docs/week_notes/week1_pricer_review.md).
