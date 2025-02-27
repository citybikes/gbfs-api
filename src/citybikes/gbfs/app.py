import contextlib
import os

from starlette.applications import Starlette
from starlette.routing import Mount

from citybikes.db import CBD, get_session
from citybikes.gbfs.api import Gbfs


DB_URI = os.getenv("DB_URI", "citybikes.db")


@contextlib.asynccontextmanager
async def lifespan(app):
    async with get_session(DB_URI) as db:
        app.db = CBD(db)
        yield


gbfs_v3 = Gbfs()

# XXX Handle multiple versions
routes = [
    Mount("/3", routes=gbfs_v3.routes),
]

app = Starlette(
    routes=routes,
    lifespan=lifespan,
)
