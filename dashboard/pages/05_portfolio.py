"""
05_portfolio.py — Portfolio decision layer.
Top BUY positions with capital allocation weights,
filtered by LLM risk assessment.
"""

import os
import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

st.title("💼 Portfolio")
st.caption("Top BUY positions — equal weight allocation, LLM risk filtered")


@st.cache_resource
def get_engine():
    return create_engine(
        f"postgresql+psycopg2://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
        f"@{os.environ['POSTGRES_HOST']}:{os.environ.get('POSTGRES_PORT', 5432)}/{os.environ['POSTGRES_DB']}"
    )


@st.cache_data(ttl=300)
def load_portfolio():
    query = text("""
        select ticker, run_date, signal, score, weight,
               close_price, conviction, risk_flag,
               excluded, exclusion_reason
        from portfolio_positions
        where run_date = (select max(run_date) from portfolio_positions)
        order by excluded asc, score desc
    """)
    with get_engine().connect() as conn:
        return pd.read_sql(query, conn)


df = load_portfolio()

if df.empty:
    st.info("No portfolio yet. Run the signal pipeline first.")
    st.stop()

# Split into active and excluded
active   = df[df["excluded"] == False]
excluded = df[df["excluded"] == True]

run_date = df["run_date"].max()
st.markdown(f"**Portfolio date:** {run_date}")

# ── Summary metrics ──
col1, col2, col3 = st.columns(3)
col1.metric("Active Positions", len(active))
col2.metric("Excluded by LLM", len(excluded))
col3.metric("Weight per Position", f"{active['weight'].mean()*100:.1f}%" if not active.empty else "—")

# ── Active positions ──
st.subheader("Active Positions")
if not active.empty:
    fig = px.bar(
        active,
        x="ticker",
        y="score",
        color="conviction",
        color_discrete_map={
            "High":   "#28a745",
            "Medium": "#ffc107",
            "Low":    "#fd7e14",
            None:     "#6c757d",
        },
        title="Portfolio Positions by Score (colour = LLM conviction)",
        labels={"score": "Signal Score", "ticker": "Ticker"},
    )
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(
        active[["ticker", "score", "weight", "close_price", "conviction", "risk_flag"]],
        use_container_width=True,
    )
else:
    st.info("No active positions today.")

# ── Excluded positions ──
if not excluded.empty:
    st.subheader("Excluded by LLM Risk Filter")
    st.dataframe(
        excluded[["ticker", "score", "risk_flag", "exclusion_reason"]],
        use_container_width=True,
    )