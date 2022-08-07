from fastapi import FastAPI, Depends, Request
from fastapi.staticfiles import StaticFiles

from .routers.documents import articles, tweets
from .routers.users import feeds, collections
from .routers import auth

from . import config_options

from modules.elastic import elasticDB

app = FastAPI(root_path="/api")

app.include_router(articles.router, prefix="/articles", tags=["articles", "documents"])

app.include_router(tweets.router, prefix="/tweets", tags=["tweets", "documents"])

app.include_router(auth.router, prefix="/auth", tags=["authorization"])

app.include_router(feeds.router, prefix="/users/feeds", tags=["users", "feed"])

app.include_router(
    collections.router, prefix="/users/collections", tags=["users", "collections"]
)

app.mount("/", StaticFiles(directory=config_options.FRONTEND_PATH, html=True), name="static")
