import contextlib
import os
import sqlite3

import aiosqlite
from starlette.applications import Starlette
from starlette.routing import Mount

from citybikes.db import CBD, get_session
from citybikes.gbfs.api import Gbfs


@contextlib.asynccontextmanager
async def lifespan(app):
    async with get_session() as db:
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
