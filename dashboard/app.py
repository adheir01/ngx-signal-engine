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
st.caption("Nigerian Stock Exchange — Technical Signals, Backtesting & LLM Analysis")

st.markdown("""
Navigate using the sidebar:

- **Signals** — Current BUY / SELL / HOLD signals with Gemini explanations
- **Opportunities** — Top ranked tickers by signal strength
- **Backtest** — Historical strategy performance, win rate, drawdown
- **NGX vs Global** — Price behaviour comparison across markets
""")
