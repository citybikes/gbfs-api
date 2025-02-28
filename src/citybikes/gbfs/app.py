import contextlib
import os

from starlette.applications import Starlette
from starlette.routing import Mount

from citybikes.db import CBD, get_session
from citybikes.gbfs.versions.v3.api import Gbfs as Gbfs3
from citybikes.gbfs.versions.v2.api import Gbfs as Gbfs2


DB_URI = os.getenv("DB_URI", "citybikes.db")


VERSIONS = [Gbfs2.GBFS.version, Gbfs3.GBFS.version]


@contextlib.asynccontextmanager
async def lifespan(app):
    async with get_session(DB_URI) as db:
        app.db = CBD(db)
        # XXX best way to avoid circular imports
        app.VERSIONS = VERSIONS
        yield


gbfs_v2 = Gbfs2()
gbfs_v3 = Gbfs3()

routes = [
    Mount("/2", routes=gbfs_v2.routes),
    Mount("/3", routes=gbfs_v3.routes),
]

app = Starlette(
    routes=routes,
    lifespan=lifespan,
)
