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
| Data | ngxgroup.com CSVs + yfinance |
| Infrastructure | Docker + docker-compose |

## Quick Start

```bash
# 1. Copy env file and fill in credentials
cp .env.example .env

# 2. Start the database
docker-compose up db -d

# 3. Copy-paste daily NGX price table into Excel, save as CSV, place in ./data/
See NGX CSV Format section below for details

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

Place CSV files in `./data/`. Download directly from:
https://ngxgroup.com/exchange/data/equities-price-list/

The scraper accepts raw NGX exports. Supported column names:
- Date or Trade Date
- Company or Symbol
- Opening Price or Open
- High, Low, Close, Volume

Note: `--` values in High/Low/Volume are handled automatically.
NGX does not provide historical data via free download — collect
daily exports manually. 30 trading days minimum for meaningful signals.

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

## Troubleshooting

**Container not picking up code changes**
Delete the cached image and rebuild:
```bash
docker rmi ngx-signal-engine-ingestion
docker-compose build --no-cache ingestion
```

**Orphan containers warning**
```bash
docker-compose down --remove-orphans
```

**No signals showing on dashboard**
Signals require minimum 14–20 days of price history per ticker
for RSI and SMA indicators to compute. Collect daily CSVs and
re-run ingestion + signals each day.

**dbt mart tables missing (Comparison page empty)**
```bash
cd dbt
dbt run
```
