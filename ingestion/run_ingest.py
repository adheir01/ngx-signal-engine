"""
run_ingest.py
Entry point — loads NGX CSV data and global yfinance data into PostgreSQL.
"""

import logging
from db_writer import get_session, NGXPrice, GlobalPrice, IngestAudit, upsert_prices
from ngx_scraper import load_all_csvs
from yfinance_loader import fetch_global_prices

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run():
    session = get_session()

    # ── NGX ──
    logger.info("=== NGX ingestion ===")
    ngx_rows = load_all_csvs()
    ngx_inserted, ngx_skipped = upsert_prices(session, NGXPrice, ngx_rows)
    logger.info(f"NGX: inserted={ngx_inserted}, skipped={ngx_skipped}")

    session.add(IngestAudit(
        source="NGX_CSV",
        tickers_loaded=list({r["ticker"] for r in ngx_rows}),
        rows_inserted=ngx_inserted,
        rows_skipped=ngx_skipped,
        errors=[],
    ))
    session.commit()

    # ── Global ──
    logger.info("=== Global (yfinance) ingestion ===")
    global_rows = fetch_global_prices()
    g_inserted, g_skipped = upsert_prices(session, GlobalPrice, global_rows)
    logger.info(f"Global: inserted={g_inserted}, skipped={g_skipped}")

    session.add(IngestAudit(
        source="YFINANCE",
        tickers_loaded=list({r["ticker"] for r in global_rows}),
        rows_inserted=g_inserted,
        rows_skipped=g_skipped,
        errors=[],
    ))
    session.commit()
    session.close()
    logger.info("Ingestion complete.")


if __name__ == "__main__":
    run()
