import asyncio
import os
from datetime import datetime
from eaia.logging import setup_logging


async def run_once(minutes_since: int = 15):
    from scripts.run_ingest import main as ingest_main
    await ingest_main(minutes_since=minutes_since)


async def main():
    logger = setup_logging("eaia.scheduler")
    interval = int(os.getenv("EAIA_INTERVAL_SEC", "300"))
    window = int(os.getenv("EAIA_WINDOW_MIN", "15"))
    logger.info(f"Scheduler started interval={interval}s window={window}m")
    while True:
        try:
            logger.info("Run start")
            await run_once(minutes_since=window)
            logger.info("Run complete")
        except Exception as e:
            logger.exception(f"Run failed: {e}")
        await asyncio.sleep(interval)


if __name__ == "__main__":
    asyncio.run(main())



