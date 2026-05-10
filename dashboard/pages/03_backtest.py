"""
03_backtest.py — Backtest results: win rate, returns, drawdown.
"""

import os
import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

st.title("📊 Backtest Results")


@st.cache_resource
def get_engine():
    return create_engine(
        f"postgresql+psycopg2://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
        f"@{os.environ['POSTGRES_HOST']}:{os.environ.get('POSTGRES_PORT', 5432)}/{os.environ['POSTGRES_DB']}"
    )


@st.cache_data(ttl=600)
def load_backtest_summary():
    query = text("""
        select distinct on (ticker)
            ticker, total_trades, win_rate, avg_return_pct, max_drawdown, sharpe_ratio, run_at
        from backtest_runs
        order by ticker, run_at desc
    """)
    with get_engine().connect() as conn:
        return pd.read_sql(query, conn)


df = load_backtest_summary()

if df.empty:
    st.info("No backtest results yet.")
    st.stop()

col1, col2, col3 = st.columns(3)
col1.metric("Avg Win Rate", f"{df['win_rate'].mean()*100:.1f}%")
col2.metric("Avg Return/Trade", f"{df['avg_return_pct'].mean():.2f}%")
col3.metric("Avg Max Drawdown", f"{df['max_drawdown'].mean():.2f}%")

fig = px.scatter(
    df,
    x="win_rate",
    y="avg_return_pct",
    size="total_trades",
    color="sharpe_ratio",
    hover_name="ticker",
    title="Win Rate vs Avg Return (bubble = trade count)",
    labels={"win_rate": "Win Rate", "avg_return_pct": "Avg Return %"},
)
st.plotly_chart(fig, use_container_width=True)
st.dataframe(df.sort_values("avg_return_pct", ascending=False), use_container_width=True)
