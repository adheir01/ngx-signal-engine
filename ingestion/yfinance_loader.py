"""
yfinance_loader.py
Fetches EU/US comparison price data via yfinance.

Markets tracked:
  - DAX 40 sample  (Germany — closest comparison for Statista context)
  - S&P 500 sample (US benchmark)
  - FTSE 100 sample (UK)
"""

import logging
from datetime import date, timedelta

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

# Representative tickers — extend as needed
COMPARISON_TICKERS = {
    "DAX":   ["SAP.DE", "SIE.DE", "ALV.DE", "DTE.DE", "MBG.DE"],
    "SP500": ["AAPL", "MSFT", "GOOGL", "AMZN", "META"],
    "FTSE":  ["SHEL.L", "AZN.L", "HSBA.L", "ULVR.L", "BP.L"],
}

DEFAULT_LOOKBACK_DAYS = 365


def fetch_global_prices(
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> list[dict]:
    """
    Download OHLCV data for all comparison tickers.
    Returns a list of price dicts ready for db_writer.upsert_prices().
    """
    end_date   = date.today()
    start_date = end_date - timedelta(days=lookback_days)
    all_rows: list[dict] = []

    for market, tickers in COMPARISON_TICKERS.items():
        logger.info(f"Fetching {market} tickers: {tickers}")
        for ticker in tickers:
            try:
                df = yf.download(
                    ticker,
                    start=start_date.isoformat(),
                    end=end_date.isoformat(),
                    progress=False,
                    auto_adjust=True,
                )
                if df.empty:
                    logger.warning(f"No data returned for {ticker}")
                    continue

                df = df.reset_index()
                # Newer yfinance returns MultiIndex columns — flatten to single level
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [col[0].lower() if col[0] != "" else col[1].lower() 
                                for col in df.columns]
                else:
                    df.columns = df.columns.str.lower()

                rows = []
                for _, row in df.iterrows():
                    rows.append({
                        "ticker":      ticker,
                        "trade_date":  row["date"].date() if hasattr(row["date"], "date") else row["date"],
                        "open_price":  round(float(row.get("open", 0) or 0), 4),
                        "high_price":  round(float(row.get("high", 0) or 0), 4),
                        "low_price":   round(float(row.get("low", 0) or 0), 4),
                        "close_price": round(float(row["close"]), 4),
                        "volume":      int(row.get("volume", 0) or 0),
                        "market":      market,
                    })
                all_rows.extend(rows)
                logger.info(f"  {ticker}: {len(rows)} rows")

            except Exception as e:
                logger.error(f"Failed to fetch {ticker}: {e}")

    return all_rows
