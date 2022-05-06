from fastapi import FastAPI, Depends, Request
from .routers.documents import articles, tweets
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

@app.get("/")
async def root():
    return {"message": "Hello World"}
