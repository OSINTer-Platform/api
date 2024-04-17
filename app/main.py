from typing import Any, Callable
from urllib.parse import parse_qsl, urlencode
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .routers import auth, ml
from .routers.documents import articles
from .routers.documents import cves
from .routers.subscriptions import feeds, collections
from .routers import user_items
from .routers import user
from .routers import survey

app = FastAPI(
    root_path="",
)


@app.middleware("http")
async def filter_blank_query_params(
    request: Request, call_next: Callable[..., Any]
) -> Any:
    scope = request.scope
    if scope and scope.get("query_string"):
        filtered_query_params = parse_qsl(
            qs=scope["query_string"].decode("latin-1"),
            keep_blank_values=False,
        )
        scope["query_string"] = urlencode(filtered_query_params).encode("latin-1")
    return await call_next(request)


@app.exception_handler(Exception)
async def custom_internal_error_handler(_: Any, __: Any) -> JSONResponse:
    return JSONResponse({"detail": "Internal server error"}, 500)


app.include_router(articles.router, prefix="/articles", tags=["articles"])

app.include_router(cves.router, prefix="/cves", tags=["cves"])

app.include_router(auth.router, prefix="/auth", tags=["authorization"])

app.include_router(feeds.router, prefix="/my/feeds", tags=["feed"])

app.include_router(collections.router, prefix="/my/collections", tags=["collections"])

app.include_router(user.router, prefix="/my/user", tags=["user"])

app.include_router(user_items.router, prefix="/user-items", tags=["user-items"])

app.include_router(survey.router, prefix="/surveys", tags=["survey"])

ml.mount_routers()
app.include_router(ml.router, prefix="/ml", tags=["ml"])
