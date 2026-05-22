"""
portfolio.py
Constructs a portfolio from today's BUY signals.

Logic:
  1. Take all BUY signals scored today
  2. Filter out HIGH risk (from LLM) and LOW conviction signals
  3. Rank by score descending
  4. Take top N (default 5)
  5. Equal weight allocation
  6. Save to portfolio_positions table

This is the decision layer — turns signals into actionable allocations.
LLM output directly influences what makes it into the portfolio.
"""

import logging
import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ingestion"))

import pandas as pd
from sqlalchemy import text

from db_writer import get_session, PortfolioPosition

logger = logging.getLogger(__name__)

TOP_N = 5


def load_todays_signals(session) -> pd.DataFrame:
    """Load today's BUY signals with LLM output joined."""
    query = text("""
        select
            s.ticker,
            s.trade_date,
            s.signal,
            s.signal_strength  as score,
            s.close_price,
            e.conviction,
            e.risk_flag,
            e.explanation
        from signals s
        left join signal_explanations e on s.id = e.signal_id
        where s.signal = 'BUY'
        and s.trade_date = :today
        order by s.signal_strength desc
    """)
    with session.bind.connect() as conn:
        return pd.read_sql(query, conn, params={"today": date.today()})


def construct_portfolio(df: pd.DataFrame, top_n: int = TOP_N) -> list[dict]:
    """
    Filter, rank and weight BUY signals into portfolio positions.

    LLM influence:
    - conviction = Low  → score penalty, pushed down rankings
    - risk_flag = HIGH  → excluded from portfolio entirely
    """
    if df.empty:
        logger.warning("No BUY signals to construct portfolio from.")
        return []

    results = []

    for _, row in df.iterrows():
        score        = float(row["score"] or 0)
        conviction   = row.get("conviction")
        risk_flag    = row.get("risk_flag")
        excluded     = False
        reason       = None

        # LLM risk filter — exclude HIGH risk positions
        if risk_flag == "HIGH":
            excluded = True
            reason   = "LLM risk flag: HIGH"

        # LLM conviction adjustment — penalise low conviction
        if conviction == "Low":
            score -= 5
            logger.info(f"{row['ticker']}: score adjusted -5 for Low conviction")

        results.append({
            "ticker":          row["ticker"],
            "signal":          row["signal"],
            "score":           score,
            "close_price":     row["close_price"],
            "conviction":      conviction,
            "risk_flag":       risk_flag,
            "excluded":        excluded,
            "exclusion_reason": reason,
        })

    # Separate excluded from eligible
    eligible = [r for r in results if not r["excluded"]]
    excluded = [r for r in results if r["excluded"]]

    # Rank eligible by adjusted score, take top N
    eligible = sorted(eligible, key=lambda x: x["score"], reverse=True)[:top_n]

    # Equal weight allocation
    weight = round(1 / len(eligible), 4) if eligible else 0
    for r in eligible:
        r["weight"] = weight

    # Excluded positions get weight 0
    for r in excluded:
        r["weight"] = 0

    all_positions = eligible + excluded
    logger.info(
        f"Portfolio: {len(eligible)} positions @ {weight*100:.1f}% each | "
        f"{len(excluded)} excluded by LLM risk filter"
    )
    return all_positions


def save_portfolio(session, positions: list[dict]) -> int:
    """Persist portfolio positions to DB."""
    today   = date.today()
    saved   = 0

    for pos in positions:
        existing = session.query(PortfolioPosition).filter_by(
            run_date=today, ticker=pos["ticker"]
        ).first()
        if existing:
            continue

        session.add(PortfolioPosition(
            run_date         = today,
            ticker           = pos["ticker"],
            signal           = pos["signal"],
            score            = pos["score"],
            weight           = pos.get("weight", 0),
            close_price      = pos["close_price"],
            conviction       = pos.get("conviction"),
            risk_flag        = pos.get("risk_flag"),
            excluded         = pos.get("excluded", False),
            exclusion_reason = pos.get("exclusion_reason"),
        ))
        saved += 1

    session.commit()
    return saved


def run_portfolio():
    """Entry point — build and save today's portfolio."""
    session   = get_session()
    df        = load_todays_signals(session)
    positions = construct_portfolio(df)
    saved     = save_portfolio(session, positions)
    session.close()
    logger.info(f"Portfolio saved: {saved} positions for {date.today()}")
    return positions