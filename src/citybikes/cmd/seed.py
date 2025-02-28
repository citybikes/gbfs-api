import os
from importlib import resources

from citybikes.db import get_session

DB_URI = os.getenv("DB_URI", "citybikes.db")


if __name__ == "__main__":
    test_data = resources.files("tests") / "fixtures/test_data.sql"
    with get_session(DB_URI) as db:
        db.executescript(test_data.read_text())
