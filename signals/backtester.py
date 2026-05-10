"""
backtester.py
Simulates trades on historical price data using the signal engine.

Strategy: enter on BUY signal, exit on SELL signal or after max_hold_days.
Records results into backtest_runs + backtest_trades via ORM.
"""

import logging
from datetime import date
from dataclasses import asdict

import pandas as pd

from signal_engine import SignalConfig, generate_signal

logger = logging.getLogger(__name__)


def run_backtest(
    df: pd.DataFrame,
    ticker: str,
    run_name: str,
    config: SignalConfig = None,
    max_hold_days: int = 20,
) -> dict:
    """
    Simulate trades for a single ticker.

    Returns a dict with summary stats and a list of individual trades,
    ready to insert into backtest_runs + backtest_trades via ORM.
    """
    config = config or SignalConfig()
    df = df[df["ticker"] == ticker].sort_values("trade_date").copy()

    if len(df) < 30:
        logger.warning(f"Not enough data for {ticker} backtest ({len(df)} rows)")
        return {}

    trades = []
    in_trade = False
    entry_price = None
    entry_date = None
    days_held = 0

    for i, row in df.iterrows():
        sig = generate_signal(row, config)
        signal = sig["signal"]
        close  = row["close_price"]
        tdate  = row["trade_date"]

        if not in_trade and signal == "BUY":
            in_trade    = True
            entry_price = close
            entry_date  = tdate
            days_held   = 0

        elif in_trade:
            days_held += 1
            exit_triggered = signal == "SELL" or days_held >= max_hold_days

            if exit_triggered:
                ret = ((close - entry_price) / entry_price) * 100
                trades.append({
                    "ticker":          ticker,
                    "entry_date":      entry_date,
                    "exit_date":       tdate,
                    "entry_price":     round(float(entry_price), 4),
                    "exit_price":      round(float(close), 4),
                    "return_pct":      round(ret, 4),
                    "signal_at_entry": "BUY",
                    "outcome":         "WIN" if ret > 0 else "LOSS",
                })
                in_trade = False

    # Handle open position at end of data
    if in_trade:
        last = df.iloc[-1]
        ret = ((last["close_price"] - entry_price) / entry_price) * 100
        trades.append({
            "ticker":          ticker,
            "entry_date":      entry_date,
            "exit_date":       None,
            "entry_price":     round(float(entry_price), 4),
            "exit_price":      round(float(last["close_price"]), 4),
            "return_pct":      round(ret, 4),
            "signal_at_entry": "BUY",
            "outcome":         "OPEN",
        })

    if not trades:
        logger.info(f"No trades generated for {ticker}")
        return {}

    returns = [t["return_pct"] for t in trades if t["outcome"] != "OPEN"]
    wins    = [r for r in returns if r > 0]

    # Max drawdown (simplified: peak-to-trough on cumulative returns)
    cum = pd.Series([0.0] + returns).cumsum()
    max_drawdown = float((cum - cum.cummax()).min())

    sharpe = (pd.Series(returns).mean() / pd.Series(returns).std()) if len(returns) > 1 else 0.0

    summary = {
        "run_name":        run_name,
        "ticker":          ticker,
        "start_date":      df["trade_date"].min(),
        "end_date":        df["trade_date"].max(),
        "strategy_config": asdict(config) if config else {},
        "total_trades":    len(trades),
        "win_rate":        round(len(wins) / len(returns), 4) if returns else 0,
        "avg_return_pct":  round(sum(returns) / len(returns), 4) if returns else 0,
        "max_drawdown":    round(max_drawdown, 4),
        "sharpe_ratio":    round(float(sharpe), 4),
        "trades":          trades,
    }
    return summary
