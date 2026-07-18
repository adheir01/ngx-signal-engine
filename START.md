# NGX Signal Engine — Daily Startup Guide

## Every time you start your PC

```powershell
cd C:\Users\adeba\Desktop\ngx-signal-engine
docker-compose down --remove-orphans
docker-compose up db scheduler dashboard -d
```

Open http://localhost:8504

---

## Check if today's data is in the database

```powershell
docker exec -it ngx-signal-engine-db-1 psql -U ngx_user -d ngx_signals -c "SELECT COUNT(*), trade_date FROM ngx_prices GROUP BY trade_date ORDER BY trade_date DESC LIMIT 5;"
```

```powershell
docker exec -it ngx-signal-engine-db-1 psql -U ngx_user -d ngx_signals -c "SELECT COUNT(*), trade_date FROM signals GROUP BY trade_date ORDER BY trade_date DESC LIMIT 5;"
```

---

## If scheduler missed a day (PC was off at 4pm WAT)

```powershell
docker-compose run --rm ingestion
.\run_pipeline.ps1
```

---

## Scrape yesterday's data (before market opens)

Run before 10am WAT — API returns previous day's prices:

```powershell
docker-compose run --rm ingestion
```

Then run pipeline after market closes (after 2pm German time):

```powershell
docker-compose run --rm ingestion
.\run_pipeline.ps1
```

---

## Full pipeline (dbt + signals) — manual run

```powershell
.\run_pipeline.ps1
```

---

## Useful checks

**Scheduler running?**
```powershell
docker-compose logs scheduler --tail=20
```

**What's in the audit log?**
```powershell
docker exec -it ngx-signal-engine-db-1 psql -U ngx_user -d ngx_signals -c "SELECT source, rows_inserted, rows_skipped, run_at FROM ingest_audit ORDER BY run_at DESC LIMIT 5;"
```

**Clean up orphan containers**
```powershell
docker-compose down --remove-orphans
```