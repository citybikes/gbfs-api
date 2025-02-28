import sqlite3
import logging
from importlib import resources
from contextlib import asynccontextmanager

import aiosqlite

log = logging.getLogger("db")

# XXX: try to dedupe with db/__init__.py

async def migrate(conn):
    migrations_path = resources.files("citybikes.db") / "migrations"
    migrations = sorted(list(migrations_path.glob("*.sql")))
    version = await (await conn.execute("PRAGMA user_version")).fetchone()
    version = version["user_version"]
    for migration in migrations[version:]:
        cur = await conn.cursor()
        try:
            log.info("Applying %s", migration.name)
            await cur.executescript("begin;" + migration.read_text())
        except Exception as e:
            log.error("Failed migration %s: %s. Bye", migration.name, e)
            await cur.execute("rollback")
            return False
        else:
            await cur.execute("commit")

    return True


@staticmethod
@asynccontextmanager
async def get_session(*args, **kwargs):
    async with aiosqlite.connect(*args, **kwargs) as db:
        # XXX Check perf penalty on this
        db.row_factory = lambda *a: dict(sqlite3.Row(*a))
        yield db


# class shortcuts
from citybikes.db.cbd import CBD as CBD  # NOQA
