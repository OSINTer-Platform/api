from fastapi import FastAPI, Depends, Request
from .routers.documents import articles, tweets

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

@app.get("/")
async def root():
    return {"message": "Hello World"}
