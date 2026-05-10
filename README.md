# Project 04 — NGX Stock Signal Engine

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
| Data | ngxgroup.com CSVs + yfinance |
| Infrastructure | Docker + docker-compose |

## Quick Start

```bash
# 1. Copy env file and fill in credentials
cp .env.example .env

# 2. Start the database
docker-compose up db -d

# 3. Place NGX CSV exports in ./data/

# 4. Run ingestion
docker-compose run ingestion

# 5. Run signal pipeline
docker-compose run signals

# 6. Run dbt transforms
cd dbt && dbt run

# 7. Launch dashboard
docker-compose up dashboard
# Visit http://localhost:8504
```

## NGX CSV Format

Place CSV files in `./data/`. Expected columns:

```
Date, Symbol, Open, High, Low, Close, Volume
```

Export from: https://ngxgroup.com/exchange/data/equities-price-list/

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

## Port Reference (all projects)

| Project | DB port | App port |
|---|---|---|
| P01 Instagram Fake Detector | 5432 | 8501 |
| P02 Influencer ROI Scorer | 5433 | 8502 |
| P03 Engagement Anomaly Dashboard | 5434 | 8503 |
| Tribe AdCortex | 5435 | — |
| **P04 NGX Signal Engine** | **5436** | **8504** |
