from fastapi import FastAPI, Depends, Request
from .routers.documents import articles, tweets
from .routers.users import feeds
from .routers import auth

from . import config_options

from OSINTmodules.OSINTelastic import elasticDB

app = FastAPI()

app.include_router(
        articles.router,
        prefix = "/articles",
        tags=["articles", "documents"]
    )

app.include_router(
        tweets.router,
        prefix = "/tweets",
        tags=["tweets", "documents"]
    )

app.include_router(
        auth.router,
        prefix = "/auth",
        tags=["authorization"]
    )

app.include_router(
        feeds.router,
        prefix = "/users/feeds",
        tags=["users", "feed"]
    )


@app.get("/")
async def root():
    return {"message": "Hello World"}
