"""
app.py — NGX Signal Engine dashboard entry point.
"""

import streamlit as st

st.set_page_config(
    page_title="NGX Signal Engine",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📈 NGX Stock Signal Engine")
st.caption("Nigerian Stock Exchange — Technical Signals, Backtesting & LLM-Filtered Decisions")

st.markdown("""
A personal investment decision system for the Nigerian Stock Exchange.
Price discovery on NGX is slower and data quality is lower than EU/US markets —
this system compensates with automated daily data collection, technical signal
generation, and LLM-filtered portfolio construction.
""")

st.divider()

st.subheader("How it works")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**1. Data**")
    st.markdown("""
    NGX equities fetched daily from the NGX JSON API.
    EU/US comparison data via yfinance.
    146 tickers tracked automatically.
    """)

with col2:
    st.markdown("**2. Features + Signals**")
    st.markdown("""
    Features computed in dbt — returns, momentum,
    SMA/EMA, volume ratio. Python scoring layer
    produces BUY / SELL / HOLD with a strength score.
    """)

with col3:
    st.markdown("**3. Decision**")
    st.markdown("""
    Gemini 2.5 Flash explains high-conviction signals
    and flags risk. HIGH risk signals are excluded from
    the portfolio. Top 5 BUY positions get equal weight.
    """)

st.divider()

st.subheader("Navigate")
st.markdown("""
- **🔔 Signals** — All BUY / SELL / HOLD signals for today with LLM explanations
- **🎯 Opportunities** — Top ranked BUY signals by strength
- **📊 Backtest** — Historical strategy performance, win rate, drawdown
- **🌍 NGX vs Global** — How NGX price behaviour compares to DAX, S&P 500, FTSE
- **💼 Portfolio** — Today's top 5 positions, equal weight, LLM risk filtered
""")