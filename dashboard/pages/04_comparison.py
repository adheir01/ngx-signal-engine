"""
04_comparison.py — NGX vs EU/US price behaviour comparison.
"""

import os
import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

st.title("🌍 NGX vs Global Markets")
st.caption("Comparing price discovery speed, volatility, and volume consistency")


@st.cache_resource
def get_engine():
    return create_engine(
        f"postgresql+psycopg2://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
        f"@{os.environ['POSTGRES_HOST']}:{os.environ.get('POSTGRES_PORT', 5432)}/{os.environ['POSTGRES_DB']}"
    )


@st.cache_data(ttl=600)
def load_comparison():
    try:
        query = text("""
            select market, trade_date, avg_close, price_stddev, avg_volume
            from analytics.mart_ngx_vs_global
            order by market, trade_date
        """)
        with get_engine().connect() as conn:
            return pd.read_sql(query, conn)
    except Exception:
        return pd.DataFrame()


df = load_comparison()

if df.empty:
    st.info("Run dbt models first: dbt run --select mart_ngx_vs_global")
    st.stop()

market_filter = st.multiselect(
    "Select markets",
    df["market"].unique().tolist(),
    default=df["market"].unique().tolist(),
)
df = df[df["market"].isin(market_filter)]

fig1 = px.line(df, x="trade_date", y="price_stddev", color="market",
               title="Daily Price Volatility (StdDev) by Market")
st.plotly_chart(fig1, use_container_width=True)

fig2 = px.line(df, x="trade_date", y="avg_volume", color="market",
               title="Average Daily Volume by Market")
st.plotly_chart(fig2, use_container_width=True)

st.subheader("Summary Statistics")
summary = df.groupby("market").agg(
    avg_volatility=("price_stddev", "mean"),
    avg_volume=("avg_volume", "mean"),
    trading_days=("trade_date", "count"),
).reset_index()
st.dataframe(summary, use_container_width=True)
