"""
run_signals.py
Entry point — reads prices from DB, computes indicators,
generates signals, calls Gemini for BUY/SELL, persists all via ORM.
"""

import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ingestion"))

import pandas as pd
from sqlalchemy import select

from db_writer import (
    get_session, NGXPrice, PriceIndicator, Signal, SignalExplanation,
    BacktestRun, BacktestTrade
)
from indicators import compute_all_indicators
from signal_engine import generate_all_signals, SignalConfig
from gemini_explainer import explain_signal
from backtester import run_backtest

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def load_ngx_prices(session) -> pd.DataFrame:
    rows = session.execute(select(NGXPrice)).scalars().all()
    return pd.DataFrame([{
        "ticker":      r.ticker,
        "trade_date":  r.trade_date,
        "open_price":  r.open_price,
        "high_price":  r.high_price,
        "low_price":   r.low_price,
        "close_price": float(r.close_price),
        "volume":      r.volume,
        "market":      r.market,
    } for r in rows])


def run():
    session = get_session()
    config  = SignalConfig()

    # ── Load prices ──
    logger.info("Loading NGX prices from DB...")
    df = load_ngx_prices(session)
    if df.empty:
        logger.error("No NGX price data found. Run ingestion first.")
        return

    # ── Compute indicators per ticker ──
    logger.info("Computing indicators...")
    all_indicators = []
    for ticker, grp in df.groupby("ticker"):
        computed = compute_all_indicators(grp.copy(), config.sma_short, config.sma_long)
        all_indicators.append(computed)

    df_indicators = pd.concat(all_indicators, ignore_index=True)

    # Persist indicators
    sma_s, sma_l = config.sma_short, config.sma_long
    for _, row in df_indicators.iterrows():
        existing = session.query(PriceIndicator).filter_by(
            ticker=row["ticker"], trade_date=row["trade_date"], market=row.get("market", "NGX")
        ).first()
        if not existing:
            session.add(PriceIndicator(
                ticker        = row["ticker"],
                trade_date    = row["trade_date"],
                market        = row.get("market", "NGX"),
                pct_change_1d = row.get("pct_change_1d"),
                pct_change_5d = row.get("pct_change_5d"),
                sma_10        = row.get(f"sma_{sma_s}"),
                sma_20        = row.get(f"sma_{sma_l}"),
                ema_10        = row.get(f"ema_{sma_s}"),
                ema_20        = row.get(f"ema_{sma_l}"),
                rsi_14        = row.get("rsi_14"),
                volume_change = row.get("volume_change"),
            ))
    session.commit()
    logger.info("Indicators saved.")

    # ── Generate signals ──
    logger.info("Generating signals...")
    signals = generate_all_signals(df_indicators, config)

    for sig in signals:
        existing = session.query(Signal).filter_by(
            ticker=sig["ticker"], trade_date=sig["trade_date"]
        ).first()
        if existing:
            continue

        signal_row = Signal(**{k: v for k, v in sig.items() if k != "triggered_rules"},
                            triggered_rules=sig.get("triggered_rules", []))
        session.add(signal_row)
        session.flush()  # get signal_row.id

        # ── Gemini explanations for BUY/SELL only ──
        if sig["signal"] in ("BUY", "SELL"):
            logger.info(f"Calling Gemini for {sig['ticker']} {sig['signal']}...")
            explanation = explain_signal(sig)
            if explanation:
                session.add(SignalExplanation(
                    signal_id      = signal_row.id,
                    ticker         = sig["ticker"],
                    trade_date     = sig["trade_date"],
                    explanation    = explanation.get("explanation"),
                    risk_flag      = explanation.get("risk_flag"),
                    risk_reasoning = explanation.get("risk_reasoning"),
                    prompt_tokens  = explanation.get("prompt_tokens"),
                ))

    session.commit()
    logger.info(f"Signals saved: {len(signals)} tickers processed.")

    # ── Backtest ──
    logger.info("Running backtests...")
    tickers = df_indicators["ticker"].unique()
    for ticker in tickers:
        result = run_backtest(df_indicators, ticker, run_name="default", config=config)
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
