from contextlib import asynccontextmanager

import sqlite3
import aiosqlite

from citybikes.db.cbd import CBD as CBD


DB_URI = os.getenv("DB_URI", "citybikes.db")


@asynccontextmanager
async def get_session():
    async with aiosqlite.connect(DB_URI) as db:
        yield db
