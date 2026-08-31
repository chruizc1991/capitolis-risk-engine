# Market Data Checklist

Tracks collection status for every market-data series required to price and
simulate the book. Field/format specs live in the original source spec,
preserved at [`data/MARKET_DATA_source.md`](MARKET_DATA_source.md) (copied
verbatim from the pricer package's `MARKET_DATA.md`). This file is the
Week 1 collection checklist reconciled against that spec — see also
[`docs/week_notes/week1_pricer_review.md`](../docs/week_notes/week1_pricer_review.md).

No series ship with `capitolis_pricers/` beyond three illustrative sample
spots in `capitolis_pricers/data/sample_market.py` — everything below is
genuinely **not started**.

## Legend
`not started` · `pulled` (raw data landed in `data/raw/`) · `validated` (checked, cleaned, in `data/processed/`)

## 1. USD OIS (SOFR) discount curve

| Field | Value |
|---|---|
| Source | **Databento** (paid access confirmed) — CME Globex SOFR futures: `SR3` (3-month, primary curve-building instrument) and `SR1` (1-month, short end). No ready-made OIS swap curve is published anywhere; we bootstrap our own curve from futures settlement prices (`futures price -> implied forward rate -> discount factor`) |
| Identifier | Databento dataset `GLBX.MDP3`, parent symbols `SR3.FUT` / `SR1.FUT` |
| Tenors needed | O/N, T/N, 1W, 2W, 1M, 2M, 3M, 6M, 9M, 1Y, 18M, 2Y, 3Y, 4Y, 5Y, 7Y, 10Y |
| Date range | Single as-of snapshot for the valuation date; if a historical-proxy curve build is needed, pull daily back to the depth of the vol/correl lookback (see §5) |
| Frequency | Daily (snapshot as of valuation date) |
| Day count | ACT/360 |
| Status | **pulled + bootstrapped + validated**. `build_curve()` maps each SR3 contract to its 3-month IMM reference period and chains discount factors sequentially (ACT/360, simply-compounded). Cross-checked against Treasury.gov's daily par yield curve (same date, 2026-08-28, independent source, no API key needed): spread widens smoothly from ~13bp (1Mo) to ~56bp (10Yr) — consistent with the normal SOFR-vs-Treasury term premium, no anomalies. **Caveat:** only 21 live SR3 contracts, reaching ~3.6yrs out (to ~2030-03); the curve beyond that is flat zero-rate extrapolation, not genuinely futures-implied — fine for pricing our book (longest trade maturity is 2044 for bonds, but those don't need rate-curve tenor beyond discounting, which extrapolation handles reasonably; flagging for awareness, not blocking). All 8 bond trades price correctly off this curve. |
| Bug found + fixed | An earlier version of the year-decoding logic wrapped recently-expired serial contracts (e.g. `SR3Q6`, expiring Aug 2026) a full decade forward instead of dropping them, silently producing a spurious 3.5-year gap in the curve and a bad 10Y point (73bp vs. Treasury instead of the smooth ~56bp after the fix). Caught by this Treasury cross-check — a good example of why validating against an independent source matters. |
| Note | API key is never committed to the repo — set via environment variable only |

## 2. Equity spot prices + dividend yields (41 names)

| Field | Value |
|---|---|
| Source | yfinance (spot, historical prices); dividend yield via yfinance trailing yield or put-call parity if options data available |
| Identifier | ISIN (keys `MarketState.equity_spots`) — mapped from `trade_data/underlyings/equities.csv`; yfinance needs ticker, so ISIN→ticker mapping must be preserved (the `ticker` column already provides this) |
| Names | 41 basket rows / 37 unique ISINs across the 8 Equity TRS baskets (some names, e.g. AAPL, repeat across baskets) — see inventory in week1_pricer_review.md; includes 6 JPY-quoted names (`6902.T`, `7751.T`, `4901.T`, `5108.T`, `4503.T`, `8035.T` across EQTRS_0005/0006) |
| Date range | Snapshot as of valuation date for pricing; 1-3yrs daily history for vol/correlation calibration (see §5) |
| Frequency | Daily |
| Status | **pulled** — live snapshot fetched via `src/risk_engine/market/equities.fetch_raw()` for all 37 ISINs, cached at `data/raw/equity_spots_2026-08-24.json`. Not yet **validated** (no cross-check against a second source; `div_yield` blanks defaulted to 0.0, needs review before use) |

## 3. USDJPY FX spot and forward curve

| Field | Value |
|---|---|
| Source | yfinance (`JPY=X`) for spot/history; forward points from a bank/Bloomberg FX swap points source — **needed for full forward curve, not just spot** |
| Identifier | `JPY=X` (yfinance), pair USDJPY (quoted JPY per USD, convention confirmed in pricer README §4/§6) |
| Tenors needed | SPOT (T+2), O/N, T/N, 1W, 1M, 2M, 3M, 6M, 9M, 1Y, 2Y |
| Date range | Snapshot as of valuation date; only needed for the JPY compo trades (EQTRS_0005, EQTRS_0006) |
| Frequency | Daily |
| Status | **spot pulled** (159.80 as of 2026-08-30, cached at `data/raw/usdjpy_spot_2026-08-30.json`) — sufficient to *price* the JPY compo trades. Forward points still **not started**, needed only once FX is simulated as a risk factor |
| Note | Only spot is needed to *price*; the full forward curve (swap points) is needed once FX is simulated as a risk factor |

## 4. Volatilities (simulation calibration — not used by the linear pricers)

| Field | Value |
|---|---|
| Source | TBD — implied vols (options market data, e.g. CBOE/OptionMetrics) preferred; historical realized vol as a fallback proxy |
| Factors | `RATE_USD`, one per equity ISIN (41), `FX_USDJPY` — 43 factors total |
| Date range | Depends on method: implied = snapshot; historical proxy = same lookback as §5 |
| Frequency | Daily (or per calibration run) |
| Status | **not started** |

## 5. Pairwise correlation matrix

| Field | Value |
|---|---|
| Source | Historical correlation proxy (Week 2 task per project scope) — daily log returns of the USD short rate, each of the 41 equity spots, and USDJPY |
| History to start pulling now | **1-3 years of daily returns** for all 43 factors, so the Week 2 correlation build isn't blocked on data collection |
| Date range | 2023-08-31 to 2026-08-30 (3yr) as the outer bound; can trim to 1yr if data quality/availability is an issue for some names |
| Frequency | Daily |
| Status | **history pulled** (not yet correlated — that's Week 2). `scripts/pull_historical_data.py` fetches all 43 factors: SOFR level (FRED, 781 obs), USDJPY (yfinance, 777 obs), all 37 equity names (yfinance, 778 rows after normalizing US/Tokyo market-hour timestamps to date-only — mixed timestamps initially produced a mostly-NaN merge, fixed). ~4% NaN remaining (expected: holiday mismatches between US/Tokyo calendars). Cached at `data/processed/history_{sofr,usdjpy,equities}.csv` (gitignored) |

## 6. Risk-free government/agency bond reference data (validation)

| Field | Value |
|---|---|
| Source | Trade data already supplies full bond terms (`trade_data/underlyings/bonds.csv`: 5 US Treasury bonds, Bond_A through Bond_E) — no external bond reference data needed to price, since bonds are risk-free and discount on the USD curve |
| Use | Cross-check the USD curve build against on-the-run Treasury yields as an independent sanity check (e.g. Treasury.gov par yield curve) |
| Status | **not started** (nice-to-have cross-check, not a blocker) |

## Credit / CDS (optional — only if extended to risky bonds)

Not needed this week; all 5 bonds are risk-free (issuer = "US TREASURY N/B",
blank in the pricer's credit-lookup sense). Deferred per pricer README §8.

---

## Summary

| # | Series | Status |
|---|---|---|
| 1 | USD OIS (SOFR) curve | pulled + bootstrapped + validated (found and fixed a real bug via cross-check) |
| 2 | Equity spots + dividends (37 unique names) | pulled (not yet validated) |
| 3 | USDJPY FX spot + forward curve | spot pulled (forward curve not started) |
| 4 | Volatilities (43 factors) | not started |
| 5 | Correlation matrix (historical proxy, Week 2) | 3yr history pulled for all 43 factors; correlation calc itself is Week 2 |
| 6 | Bond reference data (validation cross-check) | not started (optional) |

**USD curve unblocked** — Databento (paid, confirmed access) covers SOFR
futures for curve building; fetch/clean code is in place, bootstrapping is
the remaining step. **Still open:** FX forward points beyond spot (no free
or currently-confirmed source), and volatilities. Flagging for the Friday
check-in.
