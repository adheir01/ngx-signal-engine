"""
signal_engine.py
Rule-based BUY / SELL / HOLD signal generator.

Rules are configurable via environment variables or passed directly.
Each fired rule contributes to a composite signal_strength score (0–100).
"""

import os
import logging
from dataclasses import dataclass, field

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class SignalConfig:
    rsi_oversold:            float = float(os.environ.get("RSI_OVERSOLD", 30))
    rsi_overbought:          float = float(os.environ.get("RSI_OVERBOUGHT", 70))
    volume_spike_multiplier: float = float(os.environ.get("VOLUME_SPIKE_MULTIPLIER", 1.5))
    sma_short:               int   = int(os.environ.get("SMA_SHORT", 10))
    sma_long:                int   = int(os.environ.get("SMA_LONG", 20))


def generate_signal(row: pd.Series, config: SignalConfig = None) -> dict:
    """
    Evaluate a single row (latest date for one ticker) and return a signal dict.

    Signal scoring:
      - RSI oversold          → +30 BUY points
      - SMA bullish crossover → +25 BUY points
      - Volume spike + up day → +20 BUY points
      - RSI overbought        → +30 SELL points
      - SMA bearish crossover → +25 SELL points
      - Volume spike + down day → +20 SELL points

    Final signal: highest scoring direction, or HOLD if tied/low.
    """
    if config is None:
        config = SignalConfig()

    buy_score  = 0
    sell_score = 0
    triggered  = []

    rsi          = row.get("rsi_14")
    sma_short    = row.get(f"sma_{config.sma_short}")
    sma_long     = row.get(f"sma_{config.sma_long}")
    volume_chg   = row.get("volume_change", 0) or 0
    pct_change   = row.get("pct_change_1d", 0) or 0

    sma_crossover = False
    volume_spike  = abs(volume_chg) >= (config.volume_spike_multiplier - 1) * 100

    # RSI rules
    if rsi is not None and not pd.isna(rsi):
        if rsi < config.rsi_oversold:
            buy_score += 30
            triggered.append(f"RSI_OVERSOLD({rsi:.1f})")
        elif rsi > config.rsi_overbought:
            sell_score += 30
            triggered.append(f"RSI_OVERBOUGHT({rsi:.1f})")

    # SMA crossover rules
    if sma_short is not None and sma_long is not None:
        if not pd.isna(sma_short) and not pd.isna(sma_long):
            if sma_short > sma_long:
                buy_score += 25
                sma_crossover = True
                triggered.append("SMA_BULLISH_CROSS")
            elif sma_short < sma_long:
                sell_score += 25
                sma_crossover = True
                triggered.append("SMA_BEARISH_CROSS")

    # Volume spike rules
    if volume_spike:
        if pct_change > 0:
            buy_score += 20
            triggered.append(f"VOLUME_SPIKE_UP({volume_chg:.0f}%)")
        else:
            sell_score += 20
            triggered.append(f"VOLUME_SPIKE_DOWN({volume_chg:.0f}%)")

    # Determine final signal
    if buy_score > sell_score and buy_score >= 25:
        signal = "BUY"
        strength = min(buy_score, 100)
    elif sell_score > buy_score and sell_score >= 25:
        signal = "SELL"
        strength = min(sell_score, 100)
    else:
        signal = "HOLD"
        strength = max(buy_score, sell_score)

    return {
        "ticker":          row["ticker"],
        "trade_date":      row["trade_date"],
        "signal":          signal,
        "signal_strength": round(strength, 2),
        "triggered_rules": triggered,
        "close_price":     row.get("close_price"),
        "rsi_14":          rsi,
        "sma_crossover":   sma_crossover,
        "volume_spike":    volume_spike,
    }


def generate_all_signals(df: pd.DataFrame, config: SignalConfig = None) -> list[dict]:
    """Generate signals for the most recent row of each ticker."""
    config = config or SignalConfig()
    latest = df.sort_values("trade_date").groupby("ticker").last().reset_index()
    return [generate_signal(row, config) for _, row in latest.iterrows()]
