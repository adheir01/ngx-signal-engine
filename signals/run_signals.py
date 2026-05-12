"""
run_signals.py
Entry point — runs dbt then scores features.

Flow:
  1. dbt run (feature computation)
  2. scoring.py (signal generation from features)
  3. backtester.py (historical performance)
"""

import logging
import os
import sys
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ingestion"))

from db_writer import get_session, NGXPrice, BacktestRun, BacktestTrade
from scoring import run_scoring
from backtester import run_backtest
from sqlalchemy import select
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def load_ngx_prices(session) -> pd.DataFrame:
    rows = session.execute(select(NGXPrice)).scalars().all()
    return pd.DataFrame([{
        "ticker":      r.ticker,
        "trade_date":  r.trade_date,
        "close_price": float(r.close_price),
        "volume":      r.volume,
        "market":      r.market,
    } for r in rows])


def run():
    # ── Step 1: dbt runs locally before this container ──
    # Run: cd dbt && dbt run  (from your terminal)
    # This container reads from analytics.fct_features which dbt populates
    logger.info("Reading features from analytics.fct_features...")

    # ── Step 2: scoring ──
    logger.info("Running scoring layer...")
    run_scoring()

    # ── Step 3: backtest ──
    logger.info("Running backtests...")
    session = get_session()
    df = load_ngx_prices(session)

    for ticker in df["ticker"].unique():
        result = run_backtest(df, ticker, run_name="default")
        if not result:
            continue
        bt_run = BacktestRun(
            run_name        = result["run_name"],
            ticker          = result["ticker"],
            start_date      = result["start_date"],
            end_date        = result["end_date"],
            strategy_config = result["strategy_config"],
            total_trades    = result["total_trades"],
            win_rate        = result["win_rate"],
            avg_return_pct  = result["avg_return_pct"],
            max_drawdown    = result["max_drawdown"],
            sharpe_ratio    = result["sharpe_ratio"],
        )
        session.add(bt_run)
        session.flush()
        for trade in result.get("trades", []):
            session.add(BacktestTrade(run_id=bt_run.id, **trade))

    session.commit()
    session.close()
    logger.info("Signal pipeline complete.")


if __name__ == "__main__":
    run()