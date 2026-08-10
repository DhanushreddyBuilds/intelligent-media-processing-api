import asyncio
import logging

from app.workers.worker import processing_worker


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)


async def main() -> None:
    await processing_worker.run()


if __name__ == "__main__":
    asyncio.run(main())