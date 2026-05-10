"""
scheduler.py
Runs the ingestion + signal pipeline once daily at 16:00 WAT (15:00 UTC).
Uses APScheduler — lightweight, no extra infrastructure needed.
"""

import logging
import subprocess
from apscheduler.schedulers.blocking import BlockingScheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

scheduler = BlockingScheduler(timezone="UTC")


@scheduler.scheduled_job("cron", hour=15, minute=0)
def daily_pipeline():
    """Run ingestion then signals every day at 15:00 UTC (16:00 WAT)."""
    logger.info("=== Scheduled pipeline starting ===")

    try:
        logger.info("Running ingestion...")
        subprocess.run(["python", "run_ingest.py"], check=True)
        logger.info("Ingestion complete.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Ingestion failed: {e}")
        return

    try:
        logger.info("Running signals...")
        subprocess.run(["python", "signals/run_signals.py"], check=True)
        logger.info("Signals complete.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Signal pipeline failed: {e}")

    logger.info("=== Scheduled pipeline complete ===")


if __name__ == "__main__":
    logger.info("Scheduler started — pipeline runs daily at 16:00 WAT")
    scheduler.start()