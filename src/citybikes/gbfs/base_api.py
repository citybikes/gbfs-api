from functools import wraps

from starlette.routing import Route
from starlette.responses import JSONResponse
from starlette.exceptions import HTTPException

from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware


class NetworkNotFoundMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        args = request.path_params
        db = request.app.db

        uid = args.get("uid", None)

        if uid and not (await db.network_exists(uid)):
            raise HTTPException(status_code=404)

        return (await call_next(request))


class GBFSApi:
    ttl = None
    GBFS = None

    def url_for(self, request, path, * args, ** kwargs):
        return str(request.url_for(f"{self.GBFS.version}:{path}", * args, ** kwargs))

    def route_decorator(self, handler):
        @wraps(handler)
        async def _handler(request):
            args = request.path_params
            db = request.app.db

            uid = args.get("uid", None)

            if uid and not (await db.network_exists(uid)):
                raise HTTPException(status_code=404)

            response = self.GBFS.Response(
                last_updated=await db.get_last_updated(uid),
                ttl=self.ttl,
                data=await handler(request, db, **args),
            )
            return JSONResponse(response.model_dump(exclude_none=True))

        return _handler


    def route(self, path, handler, * args, ** kwargs):
        name = f"{self.GBFS.version}:{path}"
        kwargs.setdefault('name', name)
        return Route(path, self.route_decorator(handler), * args, ** kwargs)
