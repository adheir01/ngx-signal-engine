"""
01_signals.py — Current signals with LLM explanations.
"""

import os
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

st.title("🔔 Current Signals")


@st.cache_resource
def get_engine():
    return create_engine(
        f"postgresql+psycopg2://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
        f"@{os.environ['POSTGRES_HOST']}:{os.environ.get('POSTGRES_PORT', 5432)}/{os.environ['POSTGRES_DB']}"
    )


@st.cache_data(ttl=300)
def load_signals():
    engine = get_engine()
    query = text("""
        select s.ticker, s.trade_date, s.signal, s.signal_strength,
               s.close_price, s.rsi_14, s.sma_crossover, s.volume_spike,
               s.triggered_rules, e.explanation, e.risk_flag, e.risk_reasoning
        from signals s
        left join signal_explanations e on s.id = e.signal_id
        order by s.trade_date desc, s.signal_strength desc
        limit 200
    """)
    with engine.connect() as conn:
        return pd.read_sql(query, conn)


df = load_signals()

if df.empty:
    st.info("No signals yet. Run the signal pipeline first.")
    st.stop()

# Filter
signal_filter = st.multiselect("Filter by signal", ["BUY", "SELL", "HOLD"], default=["BUY", "SELL"])
df = df[df["signal"].isin(signal_filter)]

# Colour map
def colour_signal(val):
    colours = {"BUY": "background-color: #d4edda", "SELL": "background-color: #f8d7da", "HOLD": ""}
    return colours.get(val, "")

st.dataframe(
    df[["ticker", "trade_date", "signal", "signal_strength", "close_price", "rsi_14", "risk_flag"]]
    .style.map(colour_signal, subset=["signal"]),
    use_container_width=True,
)

st.subheader("LLM Explanations")
for _, row in df[df["explanation"].notna()].head(10).iterrows():
    with st.expander(f"{row['ticker']} — {row['signal']} | Risk: {row['risk_flag']}"):
        st.markdown(f"**Explanation:** {row['explanation']}")
        st.markdown(f"**Risk reasoning:** {row['risk_reasoning']}")
        st.markdown(f"**Rules triggered:** {row['triggered_rules']}")
