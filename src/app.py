import contextlib
import os
import sqlite3

import aiosqlite
from starlette.applications import Starlette
from starlette.routing import Mount

from citybikes.db import CBD
from citybikes.gbfs.api import Gbfs

DB_URI = os.getenv("DB_URI", "citybikes.db")


@contextlib.asynccontextmanager
async def lifespan(app):
    async with aiosqlite.connect(DB_URI) as db:
        # XXX Check perf penalty on this
        db.row_factory = lambda *a: dict(sqlite3.Row(*a))
        app.db = CBD(db)
        yield


# XXX: set endpoint based on ENV var and listen PORT
gbfs_v3 = Gbfs(endpoint="http://localhost:8000/")

# XXX Handle multiple versions
routes = [
    Mount("/3.0", routes=gbfs_v3.routes),
]

app = Starlette(
    routes=routes,
    lifespan=lifespan,
)
