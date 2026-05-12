"""
scoring.py
Reads features from dbt fct_features mart and produces
BUY / SELL / HOLD signals via a weighted scoring approach.

Architecture:
  dbt (fct_features) → scoring.py → signals table

Replaces the old indicators.py + signal_engine.py combination.
Features are computed and tested in dbt — Python only scores.
"""

import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ingestion"))

import pandas as pd
from sqlalchemy import text

from db_writer import get_session, Signal, SignalExplanation
from gemini_explainer import explain_signal

logger = logging.getLogger(__name__)


# ── Scoring weights ───────────────────────────────────────────────────────────
# Adjust these without touching any other file.
# Total possible score: 100

WEIGHTS = {
    "momentum_positive":   10,   # 5-day momentum > 0
    "sma_bullish":         15,   # sma_10 > sma_20
    "volume_confirmation": 10,   # volume_ratio > 1.5
    "price_above_mas":     10,   # close > both MAs
    "return_1d_positive":   5,   # positive day
    # SELL weights (negative)
    "momentum_negative":  -10,
    "sma_bearish":        -15,
    "volume_selloff":     -10,
    "price_below_mas":    -10,
    "return_1d_negative":  -5,
}


def score_row(row: pd.Series) -> tuple[int, list[str]]:
    """
    Score a single feature row.
    Returns (score, triggered_rules).
    """
    score = 0
    triggered = []

    # Momentum
    if pd.notna(row.get("momentum_5d")) and row["momentum_5d"] > 0:
        score += WEIGHTS["momentum_positive"]
        triggered.append("MOMENTUM_POSITIVE")
    elif pd.notna(row.get("momentum_5d")) and row["momentum_5d"] < 0:
        score += WEIGHTS["momentum_negative"]
        triggered.append("MOMENTUM_NEGATIVE")

    # SMA trend
    if pd.notna(row.get("sma_trend")):
        if row["sma_trend"] == "bullish":
            score += WEIGHTS["sma_bullish"]
            triggered.append("SMA_BULLISH")
        elif row["sma_trend"] == "bearish":
            score += WEIGHTS["sma_bearish"]
            triggered.append("SMA_BEARISH")

    # Volume confirmation
    if pd.notna(row.get("volume_ratio")):
        if row["volume_ratio"] > 1.5 and pd.notna(row.get("return_1d")) and row["return_1d"] > 0:
            score += WEIGHTS["volume_confirmation"]
            triggered.append("VOLUME_SPIKE_UP")
        elif row["volume_ratio"] > 1.5 and pd.notna(row.get("return_1d")) and row["return_1d"] < 0:
            score += WEIGHTS["volume_selloff"]
            triggered.append("VOLUME_SPIKE_DOWN")

    # Price above/below MAs
    if pd.notna(row.get("price_above_mas")):
        if row["price_above_mas"]:
            score += WEIGHTS["price_above_mas"]
            triggered.append("PRICE_ABOVE_MAS")
        else:
            score += WEIGHTS["price_below_mas"]
            triggered.append("PRICE_BELOW_MAS")

    # 1-day return
    if pd.notna(row.get("return_1d")):
        if row["return_1d"] > 0:
            score += WEIGHTS["return_1d_positive"]
            triggered.append(f"RETURN_1D_POS({row['return_1d']:.2f}%)")
        elif row["return_1d"] < 0:
            score += WEIGHTS["return_1d_negative"]
            triggered.append(f"RETURN_1D_NEG({row['return_1d']:.2f}%)")

    return score, triggered


def determine_signal(score: int) -> str:
    """
    Rank-based signal determination.
    Ranking > hard thresholds — avoids cliff-edge effects.
    """
    if score >= 25:
        return "BUY"
    elif score <= -15:
        return "SELL"
    else:
        return "HOLD"


def load_features(session) -> pd.DataFrame:
    """Load latest features from dbt fct_features mart."""
    query = text("""
        select distinct on (ticker)
            ticker, trade_date, market, close_price,
            return_1d, return_5d, momentum_5d,
            sma_10, sma_20, volume_ratio,
            sma_trend, volume_spike, price_above_mas
        from analytics.fct_features
        where market = 'NGX'
        order by ticker, trade_date desc
    """)
    with session.bind.connect() as conn:
        return pd.read_sql(query, conn)


def run_scoring():
    """
    Main entry point.
    Reads fct_features, scores each ticker, writes signals to DB.
    """
    session = get_session()

    logger.info("Loading features from fct_features...")
    df = load_features(session)

    if df.empty:
        logger.error("No features found. Run dbt first.")
        return

    logger.info(f"Scoring {len(df)} tickers...")
    results = []

    for _, row in df.iterrows():
        score, triggered = score_row(row)
        signal = determine_signal(score)

        results.append({
            "ticker":          row["ticker"],
            "trade_date":      row["trade_date"],
            "signal":          signal,
            "signal_strength": score,
            "triggered_rules": triggered,
            "close_price":     row["close_price"],
            "rsi_14":          None,   # RSI moved to dbt — add later
            "sma_crossover":   row["sma_trend"] in ("bullish", "bearish"),
            "volume_spike":    bool(row["volume_spike"]),
        })

    # Persist signals
    inserted = 0
    for sig in results:
        existing = session.query(Signal).filter_by(
            ticker=sig["ticker"],
            trade_date=sig["trade_date"],
        ).first()
        if existing:
            continue

        signal_row = Signal(
            ticker          = sig["ticker"],
            trade_date      = sig["trade_date"],
            signal          = sig["signal"],
            signal_strength = sig["signal_strength"],
            triggered_rules = sig["triggered_rules"],
            close_price     = sig["close_price"],
            rsi_14          = sig["rsi_14"],
            sma_crossover   = sig["sma_crossover"],
            volume_spike    = sig["volume_spike"],
        )
        session.add(signal_row)
        session.flush()
        inserted += 1

        # Gemini for BUY/SELL only
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
    session.close()

    buy_count  = sum(1 for r in results if r["signal"] == "BUY")
    sell_count = sum(1 for r in results if r["signal"] == "SELL")
    hold_count = sum(1 for r in results if r["signal"] == "HOLD")

    logger.info(f"Scoring complete — BUY: {buy_count}, SELL: {sell_count}, HOLD: {hold_count}, inserted: {inserted}")