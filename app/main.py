from typing import Any, Callable
from urllib.parse import parse_qsl, urlencode
from fastapi import FastAPI, Request

from .routers import auth, ml
from .routers.documents import articles
from .routers.subscriptions import feeds, collections
from .routers import user_items

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    root_path="/api/",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


app.include_router(articles.router, prefix="/articles", tags=["articles"])

app.include_router(auth.router, prefix="/auth", tags=["authorization"])

app.include_router(feeds.router, prefix="/my/feeds", tags=["feed"])

app.include_router(collections.router, prefix="/my/collections", tags=["collections"])

app.include_router(user_items.router, prefix="/user-items", tags=["user-items"])

ml.mount_routers()
app.include_router(ml.router, prefix="/ml", tags=["ml"])
