"""
Assembles a `capitolis_pricers.market.MarketState` from the collected market
data (sofr.py, equities.py, fx.py). Mirrors capitolis_pricers/data/sample_market.py
but sourced from real data instead of illustrative sample values.
"""


def build_market_state(ref_date):
    """Build the MarketState for `ref_date` from data/processed/. Not implemented yet."""
    raise NotImplementedError("wire up once sofr.py / equities.py / fx.py are implemented")
