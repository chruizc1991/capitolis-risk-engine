"""
Equity spot prices + dividend yields for the 41 underlying names — fetch/clean/cache.

Keyed by ISIN (see data/MARKET_DATA.md §2); ISIN->ticker mapping comes from
trade_data/underlyings/equities.csv (yfinance needs a ticker, not an ISIN).
Uses yfinance — free, no API key, good enough to unblock Week 1 while a
paid-source decision (Bloomberg/Refinitiv) is still open for rates/FX.
"""
import yfinance as yf


def _to_yfinance_symbol(ticker):
    """Our trade data uses share-class dots (e.g. BRK.B); yfinance wants
    dashes (BRK-B). Non-share-class tickers (incl. *.T for Japan) pass through."""
    if "." in ticker and not ticker.endswith(".T"):
        return ticker.replace(".", "-")
    return ticker


def fetch_raw(isin_to_ticker):
    """Pull raw last price + trailing dividend yield per ticker.

    isin_to_ticker: {isin: ticker}, e.g. from underlyings_loader baskets.
    Returns {isin: {"price": float, "currency": str, "div_yield": float|None}}.
    A ticker that errors or returns no price is skipped, not fatal to the
    batch — check the caller's log / missing-name diff against the input.
    """
    raw = {}
    for isin, ticker in isin_to_ticker.items():
        try:
            t = yf.Ticker(_to_yfinance_symbol(ticker))
            fast = t.fast_info
            price = fast.last_price
            currency = fast.currency
            div_yield = t.info.get("trailingAnnualDividendYield")
        except Exception as exc:
            print(f"WARN: fetch failed for {ticker} ({isin}): {exc}")
            continue
        raw[isin] = {
            "price": price,
            "currency": currency,
            # trailingAnnualDividendYield is already a decimal (e.g. 0.0034);
            # yfinance's plain "dividendYield" field is inconsistently scaled.
            "div_yield": div_yield,
        }
    return raw


def clean(raw):
    """Normalize into {isin: (spot, dividend_rate)}; blank dividend -> 0.0."""
    return {
        isin: (row["price"], row["div_yield"] or 0.0)
        for isin, row in raw.items()
    }


def fetch_spots(isin_to_ticker):
    """Convenience: {isin: spot} ready for MarketState.equity_spots."""
    cleaned = clean(fetch_raw(isin_to_ticker))
    return {isin: spot for isin, (spot, _) in cleaned.items()}


def fetch_dividends(isin_to_ticker):
    """Convenience: {isin: dividend_rate} ready for MarketState.equity_dividend_rates."""
    cleaned = clean(fetch_raw(isin_to_ticker))
    return {isin: div for isin, (_, div) in cleaned.items()}


def fetch_history(isin_to_ticker, start, end):
    """Daily close-price history for vol/correlation calibration (data/MARKET_DATA.md #5).
    Returns {isin: pandas.Series of closes indexed by date}."""
    history = {}
    for isin, ticker in isin_to_ticker.items():
        hist = yf.Ticker(ticker).history(start=start, end=end)
        history[isin] = hist["Close"]
    return history
