# NGX Stock Signal Engine

> Personal investment tool for the Nigerian Stock Exchange.
> Technical signals, LLM-filtered explanations, backtesting, and NGX vs EU/US comparison.

## Stack

| Layer | Tech |
|---|---|
| Language | Python 3.12 |
| Package manager | uv (native install) |
| Database | PostgreSQL 15 (port 5436) |
| ORM | SQLAlchemy 2.0 |
| Transforms | dbt |
| Dashboard | Streamlit (port 8504) |
| LLM | Gemini 2.5 Flash |
| Data | NGX JSON API + yfinance |
| Scheduler | APScheduler (daily at 16:00 WAT) |
| Infrastructure | Docker + docker-compose |

## Quick Start

```bash
# 1. Copy env file and fill in credentials
cp .env.example .env

# 2. Start everything
docker-compose up db scheduler dashboard -d

# 3. Run ingestion manually on first launch
docker-compose run ingestion

# 4. Run signal pipeline manually on first launch
docker-compose run signals

# 5. View dashboard
# http://localhost:8504
```

After first launch, ingestion and signals run automatically every day
at 16:00 WAT — no manual steps needed.

## Data Sources

### NGX (Nigerian Stock Exchange)
Fetched automatically from the NGX equities JSON API:
https://doclib.ngxgroup.com/REST/api/statistics/equities/

- All listed equities, current trading day
- Runs daily at 16:00 WAT via APScheduler
- Falls back to local CSVs in `./data/` if API is unavailable

### Global Comparison (yfinance)
DAX, S&P 500, and FTSE 100 sample tickers fetched via yfinance
for price behaviour comparison against NGX.

## Signal Rules

| Rule | Points | Direction |
|---|---|---|
| RSI < 30 (oversold) | +30 | BUY |
| SMA short > SMA long (bullish cross) | +25 | BUY |
| Volume spike on up day | +20 | BUY |
| RSI > 70 (overbought) | +30 | SELL |
| SMA short < SMA long (bearish cross) | +25 | SELL |
| Volume spike on down day | +20 | SELL |

Signal fired when score ≥ 25. Configurable via `.env`.

Meaningful signals require minimum 20 trading days of history
per ticker — RSI and SMA need sufficient price history to compute.

## Project Structure

## Pipeline Overview

```text
NGX API + CSV fallback
    ↓
Daily ingestion pipeline (APScheduler)
    ↓
PostgreSQL storage + dbt transformations
    ↓
Technical indicators (RSI, EMA, SMA, volume)
    ↓
Rule-based BUY / SELL / HOLD engine
    ↓
Backtesting + opportunity ranking
    ↓
LLM-generated signal explanations
    ↓
Streamlit dashboard
```

## Project Structure

```
ngx-signal-engine/
├── ingestion/
│   ├── ngx_scraper.py       # NGX API + CSV fallback
│   ├── yfinance_loader.py   # EU/US comparison data
│   ├── db_writer.py         # SQLAlchemy ORM models + upsert
│   ├── run_ingest.py        # ingestion entry point
│   └── scheduler.py         # APScheduler daily pipeline
├── signals/
│   ├── indicators.py        # RSI, SMA, EMA, volume change
│   ├── signal_engine.py     # BUY/SELL/HOLD rule engine
│   ├── backtester.py        # historical trade simulation
│   ├── gemini_explainer.py  # LLM explanation + risk flag
│   └── run_signals.py       # signals entry point
├── dbt/
│   └── models/
│       ├── staging/         # cleaned views over raw tables
│       └── marts/           # aggregated analytics tables
├── dashboard/
│   ├── app.py               # Streamlit entry point
│   └── pages/
│       ├── 01_signals.py        # current BUY/SELL/HOLD signals
│       ├── 02_opportunities.py  # top ranked BUY opportunities
│       ├── 03_backtest.py       # backtest results
│       └── 04_comparison.py     # NGX vs EU/US comparison
├── sql/
│   └── init.sql             # database schema
└── data/                    # local CSV fallback (gitignored)
```

## dbt

Run transforms after ingestion to populate the comparison and
performance mart tables:

```bash
cd dbt
dbt run
dbt test
```

Set environment variables first so dbt can connect:

```bash
# Windows
set POSTGRES_HOST=127.0.0.1
set POSTGRES_PORT=5436
set POSTGRES_DB=ngx_signals
set POSTGRES_USER=ngx_user
set POSTGRES_PASSWORD=your_password
```

## Troubleshooting

**Container not picking up code changes**
```bash
docker rmi ngx-signal-engine-ingestion
docker-compose build --no-cache ingestion
```

**Orphan containers warning**
```bash
docker-compose down --remove-orphans
```

**No signals on dashboard**
Signals require 14–20 days of price history per ticker for RSI
and SMA to compute. The scheduler builds this up automatically
over time.

**Comparison page empty**
Run dbt first — see dbt section above.

**Check scheduler is running**
```bash
docker-compose logs scheduler
```

## Port Reference

| Project | DB port | App port |
|---|---|---|
| P01 Instagram Fake Detector | 5432 | 8501 |
| P02 Influencer ROI Scorer | 5433 | 8502 |
| P03 Engagement Anomaly Dashboard | 5434 | 8503 |
| Tribe AdCortex | 5435 | — |
| **P04 NGX Signal Engine** | **5436** | **8504** |
