"""
indicators.py
Computes technical indicators from price data.

All functions operate on pandas DataFrames — pure computation, no DB access.
DB writes happen in run_signals.py via the ORM.
"""

import numpy as np
import pandas as pd


def compute_pct_change(df: pd.DataFrame) -> pd.DataFrame:
    """1-day and 5-day percentage price change."""
    df = df.sort_values("trade_date").copy()
    df["pct_change_1d"] = df["close_price"].pct_change(1) * 100
    df["pct_change_5d"] = df["close_price"].pct_change(5) * 100
    return df


def compute_moving_averages(df: pd.DataFrame, short: int = 10, long: int = 20) -> pd.DataFrame:
    df = df.sort_values("trade_date").copy()
    df[f"sma_{short}"] = df["close_price"].rolling(window=short).mean()
    df[f"sma_{long}"]  = df["close_price"].rolling(window=long).mean()
    df[f"ema_{short}"] = df["close_price"].ewm(span=short, adjust=False).mean()
    df[f"ema_{long}"]  = df["close_price"].ewm(span=long, adjust=False).mean()
    return df


def compute_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    df = df.sort_values("trade_date").copy()
    delta = df["close_price"].diff()
    gain  = delta.clip(lower=0)
    loss  = -delta.clip(upper=0)

    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["rsi_14"] = 100 - (100 / (1 + rs))
    return df


def compute_volume_change(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """% change vs rolling average volume — flags unusual activity."""
    df = df.sort_values("trade_date").copy()
    avg_vol = df["volume"].rolling(window=window).mean()
    df["volume_change"] = ((df["volume"] - avg_vol) / avg_vol.replace(0, np.nan)) * 100
    return df


def compute_all_indicators(df: pd.DataFrame, sma_short: int = 10, sma_long: int = 20) -> pd.DataFrame:
    """Run full indicator pipeline for a single ticker's price history."""
    df = compute_pct_change(df)
    df = compute_moving_averages(df, short=sma_short, long=sma_long)
    df = compute_rsi(df)
    df = compute_volume_change(df)
    return df
