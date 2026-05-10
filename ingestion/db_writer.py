"""
db_writer.py
SQLAlchemy ORM models and session management for NGX Signal Engine.

Why ORM instead of raw SQL?
- Parameterised bindings are handled automatically → no SQL injection risk
- Python objects instead of raw dicts → easier to refactor and test
- One place to define table structure → consistent across the app
"""

import os
from datetime import date, datetime
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import (
    BigInteger, Boolean, Column, Date, DateTime, Integer,
    Numeric, String, Text, ARRAY, ForeignKey, UniqueConstraint, Index,
    create_engine, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Session, relationship

load_dotenv()


# ── Engine ────────────────────────────────────────────────────────────────────

def get_engine():
    url = (
        f"postgresql+psycopg2://"
        f"{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
        f"@{os.environ['POSTGRES_HOST']}:{os.environ.get('POSTGRES_PORT', 5432)}"
        f"/{os.environ['POSTGRES_DB']}"
    )
    return create_engine(url, pool_pre_ping=True)


def get_session(engine=None) -> Session:
    engine = engine or get_engine()
    return Session(engine)


# ── Base ──────────────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


# ── ORM Models ────────────────────────────────────────────────────────────────

class NGXPrice(Base):
    __tablename__ = "ngx_prices"
    __table_args__ = (
        UniqueConstraint("ticker", "trade_date", name="uq_ngx_ticker_date"),
    )

    id          = Column(Integer, primary_key=True)
    ticker      = Column(String, nullable=False)
    trade_date  = Column(Date, nullable=False)
    open_price  = Column(Numeric(12, 4))
    high_price  = Column(Numeric(12, 4))
    low_price   = Column(Numeric(12, 4))
    close_price = Column(Numeric(12, 4), nullable=False)
    volume      = Column(BigInteger)
    market      = Column(String, default="NGX")
    ingested_at = Column(DateTime(timezone=True), default=func.now())


class GlobalPrice(Base):
    __tablename__ = "global_prices"
    __table_args__ = (
        UniqueConstraint("ticker", "trade_date", name="uq_global_ticker_date"),
    )

    id          = Column(Integer, primary_key=True)
    ticker      = Column(String, nullable=False)
    trade_date  = Column(Date, nullable=False)
    open_price  = Column(Numeric(12, 4))
    high_price  = Column(Numeric(12, 4))
    low_price   = Column(Numeric(12, 4))
    close_price = Column(Numeric(12, 4), nullable=False)
    volume      = Column(BigInteger)
    market      = Column(String, nullable=False)
    ingested_at = Column(DateTime(timezone=True), default=func.now())


class PriceIndicator(Base):
    __tablename__ = "price_indicators"
    __table_args__ = (
        UniqueConstraint("ticker", "trade_date", "market", name="uq_indicator_ticker_date_market"),
    )

    id            = Column(Integer, primary_key=True)
    ticker        = Column(String, nullable=False)
    trade_date    = Column(Date, nullable=False)
    market        = Column(String, nullable=False)
    pct_change_1d = Column(Numeric(8, 4))
    pct_change_5d = Column(Numeric(8, 4))
    sma_10        = Column(Numeric(12, 4))
    sma_20        = Column(Numeric(12, 4))
    ema_10        = Column(Numeric(12, 4))
    ema_20        = Column(Numeric(12, 4))
    rsi_14        = Column(Numeric(8, 4))
    volume_change = Column(Numeric(8, 4))
    computed_at   = Column(DateTime(timezone=True), default=func.now())


class Signal(Base):
    __tablename__ = "signals"
    __table_args__ = (
        UniqueConstraint("ticker", "trade_date", name="uq_signal_ticker_date"),
    )

    id              = Column(Integer, primary_key=True)
    ticker          = Column(String, nullable=False)
    trade_date      = Column(Date, nullable=False)
    signal          = Column(String, nullable=False)   # BUY / SELL / HOLD
    signal_strength = Column(Numeric(5, 2))
    triggered_rules = Column(ARRAY(Text))
    close_price     = Column(Numeric(12, 4))
    rsi_14          = Column(Numeric(8, 4))
    sma_crossover   = Column(Boolean)
    volume_spike    = Column(Boolean)
    generated_at    = Column(DateTime(timezone=True), default=func.now())

    explanation     = relationship("SignalExplanation", back_populates="signal_ref", uselist=False)


class SignalExplanation(Base):
    __tablename__ = "signal_explanations"

    id             = Column(Integer, primary_key=True)
    signal_id      = Column(Integer, ForeignKey("signals.id", ondelete="CASCADE"))
    ticker         = Column(String, nullable=False)
    trade_date     = Column(Date, nullable=False)
    llm_model      = Column(String, default="gemini-2.5-flash")
    explanation    = Column(Text)
    risk_flag      = Column(String)   # LOW / MEDIUM / HIGH
    risk_reasoning = Column(Text)
    prompt_tokens  = Column(Integer)
    generated_at   = Column(DateTime(timezone=True), default=func.now())

    signal_ref     = relationship("Signal", back_populates="explanation")


class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id              = Column(Integer, primary_key=True)
    run_name        = Column(String, nullable=False)
    ticker          = Column(String, nullable=False)
    start_date      = Column(Date, nullable=False)
    end_date        = Column(Date, nullable=False)
    strategy_config = Column(JSONB)
    total_trades    = Column(Integer)
    win_rate        = Column(Numeric(6, 4))
    avg_return_pct  = Column(Numeric(8, 4))
    max_drawdown    = Column(Numeric(8, 4))
    sharpe_ratio    = Column(Numeric(8, 4))
    run_at          = Column(DateTime(timezone=True), default=func.now())

    trades          = relationship("BacktestTrade", back_populates="run", cascade="all, delete-orphan")


class BacktestTrade(Base):
    __tablename__ = "backtest_trades"

    id              = Column(Integer, primary_key=True)
    run_id          = Column(Integer, ForeignKey("backtest_runs.id", ondelete="CASCADE"))
    ticker          = Column(String, nullable=False)
    entry_date      = Column(Date, nullable=False)
    exit_date       = Column(Date)
    entry_price     = Column(Numeric(12, 4))
    exit_price      = Column(Numeric(12, 4))
    return_pct      = Column(Numeric(8, 4))
    signal_at_entry = Column(String)
    outcome         = Column(String)   # WIN / LOSS / OPEN

    run             = relationship("BacktestRun", back_populates="trades")


class IngestAudit(Base):
    __tablename__ = "ingest_audit"

    id             = Column(Integer, primary_key=True)
    source         = Column(String, nullable=False)
    tickers_loaded = Column(ARRAY(Text))
    rows_inserted  = Column(Integer)
    rows_skipped   = Column(Integer)
    errors         = Column(ARRAY(Text))
    run_at         = Column(DateTime(timezone=True), default=func.now())


# ── Upsert helpers ────────────────────────────────────────────────────────────

def upsert_prices(session: Session, model, rows: list[dict]) -> tuple[int, int]:
    """
    Insert rows, skip on unique conflict.
    Returns (inserted, skipped) counts.
    Safe from SQL injection — SQLAlchemy handles all value binding.
    """
    inserted = 0
    skipped = 0
    for row in rows:
        exists = session.query(model).filter_by(
            ticker=row["ticker"],
            trade_date=row["trade_date"],
        ).first()
        if exists:
            skipped += 1
        else:
            session.add(model(**row))
            inserted += 1
    session.commit()
    return inserted, skipped
