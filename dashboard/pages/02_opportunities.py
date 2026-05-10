"""
02_opportunities.py — Top ranked BUY opportunities by signal strength.
"""

import os
import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

st.title("🎯 Top Opportunities")


@st.cache_resource
def get_engine():
    return create_engine(
        f"postgresql+psycopg2://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
        f"@{os.environ['POSTGRES_HOST']}:{os.environ.get('POSTGRES_PORT', 5432)}/{os.environ['POSTGRES_DB']}"
    )


@st.cache_data(ttl=300)
def load_top_buys():
    query = text("""
        select distinct on (s.ticker)
            s.ticker, s.trade_date, s.signal_strength, s.close_price, s.rsi_14,
            e.risk_flag
        from signals s
        left join signal_explanations e on s.id = e.signal_id
        where s.signal = 'BUY'
        order by s.ticker, s.trade_date desc, s.signal_strength desc
    """)
    with get_engine().connect() as conn:
        return pd.read_sql(query, conn).sort_values("signal_strength", ascending=False)


df = load_top_buys()

if df.empty:
    st.info("No BUY signals yet.")
    st.stop()

top_n = st.slider("Show top N tickers", 5, 30, 10)
df_top = df.head(top_n)

fig = px.bar(
    df_top,
    x="ticker",
    y="signal_strength",
    color="risk_flag",
    color_discrete_map={"LOW": "#28a745", "MEDIUM": "#ffc107", "HIGH": "#dc3545"},
    title="BUY Signal Strength by Ticker",
    labels={"signal_strength": "Signal Strength (0–100)"},
)
st.plotly_chart(fig, use_container_width=True)
st.dataframe(df_top, use_container_width=True)
