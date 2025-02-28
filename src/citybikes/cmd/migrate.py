import os
import sys
import asyncio
import logging

from citybikes.db import get_session, migrate


DB_URI = os.getenv("DB_URI", "citybikes.db")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


async def main():
    async with get_session(DB_URI) as db:
        return await migrate(db)


if __name__ == "__main__":
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[logging.StreamHandler(stream=sys.stderr)],
        datefmt="%H:%M:%S",
    )
    r = asyncio.run(main())
    sys.exit(int(not r))
