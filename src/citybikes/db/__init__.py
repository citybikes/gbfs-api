from contextlib import asynccontextmanager

import sqlite3
import aiosqlite

from citybikes.db.cbd import CBD as CBD


@asynccontextmanager
async def get_session(* args, ** kwargs):
    async with aiosqlite.connect(* args, ** kwargs) as db:
        # XXX Check perf penalty on this
        db.row_factory = lambda *a: dict(sqlite3.Row(*a))
        yield db
