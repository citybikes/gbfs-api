import contextlib
import os


from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.responses import Response


from citybikes.db.asyncio import CBD, get_session, migrate
from citybikes.gbfs.versions.v3.api import Gbfs as Gbfs3
from citybikes.gbfs.versions.v2.api import Gbfs as Gbfs2
from citybikes.gbfs.pages import HOME


DB_URI = os.getenv("DB_URI", "citybikes.db")


VERSIONS = [Gbfs2.GBFS.version, Gbfs3.GBFS.version]


@contextlib.asynccontextmanager
async def lifespan(app):
    async with get_session(DB_URI) as db:
        assert await migrate(db)
        app.db = CBD(db)
        # XXX best way to avoid circular imports
        app.VERSIONS = VERSIONS
        yield


gbfs_v2 = Gbfs2()
gbfs_v3 = Gbfs3()


routes = [
    Mount("/2", routes=gbfs_v2.routes),
    Mount("/3", routes=gbfs_v3.routes),
    # XXX this will do for now
    Route("/", lambda r: Response(HOME.format(endpoint=str(r.base_url)))),
]

app = Starlette(
    routes=routes,
    lifespan=lifespan,
)
