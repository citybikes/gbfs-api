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
