"""
ngx_scraper.py
Loads NGX daily price data from:
  1. Local CSV files placed in /app/data/
  2. (Placeholder) ngxgroup.com scraper — extend when site structure confirmed

Expected CSV columns (NGX format):
    Date, Symbol, Open, High, Low, Close, Volume
"""

import os
import logging
from pathlib import Path
from datetime import date

import pandas as pd

logger = logging.getLogger(__name__)

DATA_DIR = Path(os.environ.get("DATA_DIR", "/app/data"))


def _clean_numeric(series: pd.Series) -> pd.Series:
    """
    Convert a column to float, treating '--', '-', '', and other
    non-numeric values as NaN. NGX uses '--' for stocks that didn't
    trade (no High/Low recorded) — these become NULL in the database.
    """
    return pd.to_numeric(
        series.astype(str).str.strip().replace({"--": None, "-": None, "": None}),
        errors="coerce",
    )


def load_ngx_csv(filepath: Path) -> list[dict]:
    """
    Parse a single NGX CSV file into a list of price dicts.
    """
    df = pd.read_csv(filepath, na_values=["--", "-", "N/A"], keep_default_na=True)
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    rename_map = {
        "date": "trade_date",
        "trade_date": "trade_date",
        "symbol": "ticker",
        "company": "ticker",
        "opening_price": "open_price",
        "open": "open_price",
        "high": "high_price",
        "low": "low_price",
        "close": "close_price",
        "volume": "volume",
    }
    df = df.rename(columns=rename_map)

    required = {"trade_date", "ticker", "close_price"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}. Found: {list(df.columns)}")

    for col in ["open_price", "high_price", "low_price", "close_price"]:
        if col in df.columns:
            df[col] = _clean_numeric(df[col])

    if "volume" in df.columns:
        df["volume"] = pd.to_numeric(
            df["volume"].astype(str).str.replace(",", "").str.strip(),
            errors="coerce"
        ).fillna(0).astype(int)

    # Parse dates
    for fmt in ["%d %b %y", "%d %b %Y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"]:
        try:
            df["trade_date"] = pd.to_datetime(
                df["trade_date"], format=fmt, errors="raise"
            ).dt.date
            break
        except (ValueError, TypeError):
            continue
    else:
        df["trade_date"] = pd.to_datetime(
            df["trade_date"], dayfirst=True, errors="coerce"
        ).dt.date

    # ✅ These should NOT be inside the else block
    before = len(df)
    df = df.dropna(subset=["trade_date", "close_price", "ticker"])
    dropped = before - len(df)
    if dropped:
        logger.warning(f"Dropped {dropped} rows with missing date/ticker/close in {filepath.name}")

    df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
    df["market"] = "NGX"

    return df[
        ["ticker", "trade_date", "open_price", "high_price",
         "low_price", "close_price", "volume", "market"]
    ].to_dict("records")



def load_all_csvs() -> list[dict]:
    """Load every CSV in the data directory."""
    all_rows = []
    csv_files = list(DATA_DIR.glob("*.csv"))
    if not csv_files:
        logger.warning(f"No CSV files found in {DATA_DIR}")
        return []

    for f in csv_files:
        try:
            rows = load_ngx_csv(f)
            logger.info(f"Loaded {len(rows)} rows from {f.name}")
            all_rows.extend(rows)
        except Exception as e:
            logger.error(f"Failed to parse {f.name}: {e}")

    return all_rows


# ── Live API scraper ──────────────────────────────────────────────────────────
# NGX exposes an undocumented JSON API used by their equities price list page.
# Returns all tickers for the current trading day in one request.

NGX_API_URL = (
    "https://doclib.ngxgroup.com/REST/api/statistics/equities/"
    "?market=&sector=&orderby=&pageSize=300&pageNo=0"
)

NGX_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
}


def scrape_ngxgroup() -> list[dict]:
    """
    Fetch live NGX equities data from the JSON API.
    Returns price dicts ready for db_writer.upsert_prices().
    """
    import requests

    response = requests.get(NGX_API_URL, headers=NGX_HEADERS, timeout=30)
    response.raise_for_status()

    data = response.json()
    if not data:
        logger.warning("NGX API returned empty response")
        return []

    df = pd.DataFrame(data)

    rename_map = {
        "Symbol":       "ticker",
        "OpeningPrice": "open_price",
        "HighPrice":    "high_price",
        "LowPrice":     "low_price",
        "ClosePrice":   "close_price",
        "Volume":       "volume",
        "TradeDate":    "trade_date",
    }
    df = df.rename(columns=rename_map)

    df["trade_date"] = pd.to_datetime(
        df["trade_date"], errors="coerce"
    ).dt.date

    for col in ["open_price", "high_price", "low_price", "close_price"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "volume" in df.columns:
        df["volume"] = pd.to_numeric(
            df["volume"], errors="coerce"
        ).fillna(0).astype(int)

    df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
    df["market"] = "NGX"

    before = len(df)
    df = df.dropna(subset=["trade_date", "close_price", "ticker"])
    dropped = before - len(df)
    if dropped:
        logger.warning(f"Dropped {dropped} rows with missing data from API")

    logger.info(f"NGX API: fetched {len(df)} tickers for {df['trade_date'].max()}")

    return df[[
        "ticker", "trade_date", "open_price", "high_price",
        "low_price", "close_price", "volume", "market"
    ]].to_dict("records")
