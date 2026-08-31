# Capitolis Counterparty Credit Risk Engine

Monte Carlo counterparty credit risk (CCR) engine for Capitolis' ESF
derivatives book — Equity TRS (incl. JPY compo), Bond Forwards, and Bond
TRS.

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
│   ├── models/                 # stochastic risk factor models (scaffolding, not yet implemented)
│   ├── simulation/             # Monte Carlo engine (scaffolding, not yet implemented)
│   ├── exposure/                # EE/PFE/MPE aggregation (scaffolding, not yet implemented)
│   └── validation/              # analytical benchmarks (e.g. bond forward closed form)
├── scripts/                     # standalone data-pull / demo scripts
├── notebooks/                   # exploration notebooks
├── tests/                       # validation + unit tests
└── docs/
    ├── kickoff_deck.pdf
    ├── pricer_contract.md       # original capitolis_pricers/README.md
    └── notes/                    # dated check-in / review notes
```

## Install

```bash
pip install -r requirements.txt
```

or, with the package layout:

```bash
pip install -e .
```

Real data collection also needs a Databento API key set as the
`DATABENTO_API_KEY` environment variable (never committed, never passed
inline — see `src/risk_engine/market/sofr.py`).

## Run

Price the sample trades against the pricer library's illustrative sample
market (only the 4 Bond Forward / Bond TRS trades succeed against it — the
sample market only ships 3 placeholder equity spots, not the 37 real names):

```bash
python -m capitolis_pricers.examples.price_all
```

Price the full 16-trade book against real, live market data (SOFR curve via
Databento, equity spots + FX via yfinance):

```bash
python scripts/price_full_book_real_data.py
```

Pull 3 years of historical data for volatility/correlation calibration:

```bash
python scripts/pull_historical_data.py
```

Run tests:

```bash
pip install pytest
pytest tests/
```

## Status

**Done:**
- Explored `capitolis_pricers/` and read the full pricer contract
  ([`docs/pricer_contract.md`](docs/pricer_contract.md)); summarized field
  contracts and conventions in
  [`docs/notes/pricer_review.md`](docs/notes/pricer_review.md).
- Repo reorganized into the structure above; flattened the doubled
  `capitolis_pricers/capitolis_pricers/` nesting from the original zip.
- Inventoried all 16 trades by instrument type and counterparty, listed the
  41 underlying equity basket rows (37 unique names) and 5 bond types.
- Built [`data/MARKET_DATA.md`](data/MARKET_DATA.md), a per-series checklist
  (source, identifier, date range, frequency, status) for all required
  market data, reconciled against the pricer package's own spec.
- All five market data series are pulled, built, and validated: the USD
  discount curve (bootstrapped from Databento SOFR futures, cross-checked
  against Treasury.gov par yields), equity spots + dividends for all 37
  names, USDJPY spot, historical realized volatilities, and the pairwise
  correlation matrix (PSD-confirmed) — see `data/MARKET_DATA.md` for full
  detail on sources, methods, and the bugs found and fixed along the way.
- All 16 trades price successfully end-to-end against real market data
  (`scripts/price_full_book_real_data.py`).
- A validation sanity test
  ([`tests/test_bond_forward_validation.py`](tests/test_bond_forward_validation.py))
  prices a risk-free bond forward off a flat USD curve, cross-checked
  against an independent closed-form recomputation, plus directional
  (ITM/OTM/long-short-symmetry) checks.
- `models/`, `simulation/`, `exposure/` scaffolded with `__init__.py` +
  docstrings only — no modeling logic yet.

**Open:**
- FX forward points beyond spot (no confirmed source yet) — only needed
  once FX is simulated as a risk factor, not for pricing today's snapshot.
- JPY compo trade count is confirmed at 2 (`EQTRS_0005`, `EQTRS_0006`),
  resolving the earlier discrepancy against the kickoff brief.
- Next: risk factor models (`src/risk_engine/models/`), then the Monte
  Carlo simulation engine and exposure aggregation.

## Trades at a glance

| Instrument | Count | Counterparties |
|---|---|---|
| Equity TRS (incl. 2 JPY compo) | 8 | CPTY_A, CPTY_B, CPTY_C |
| Bond Forward | 4 | CPTY_A, CPTY_C |
| Bond TRS | 4 | CPTY_A, CPTY_B, CPTY_C |

41 equity basket rows / 37 unique names, 5 bond types (all US Treasuries).
Full detail in [`docs/notes/pricer_review.md`](docs/notes/pricer_review.md).
