import os
import sys
import logging

from citybikes.db import get_session, migrate


DB_URI = os.getenv("DB_URI", "citybikes.db")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


if __name__ == "__main__":
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[logging.StreamHandler(stream=sys.stderr)],
        datefmt="%H:%M:%S",
    )
    with get_session(DB_URI) as db:
        sys.exit(int(not migrate(db)))
