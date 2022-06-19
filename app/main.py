from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware

from .routers.documents import articles, tweets
from .routers.users import feeds, collections
from .routers import auth

from . import config_options

from modules.elastic import elasticDB

app = FastAPI()

origins = ["http://localhost", "http://localhost:8080", "http://localhost:8000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(articles.router, prefix="/articles", tags=["articles", "documents"])

app.include_router(tweets.router, prefix="/tweets", tags=["tweets", "documents"])

app.include_router(auth.router, prefix="/auth", tags=["authorization"])

app.include_router(feeds.router, prefix="/users/feeds", tags=["users", "feed"])

app.include_router(
    collections.router, prefix="/users/collections", tags=["users", "collections"]
)


@app.get("/")
async def root():
    return {"message": "Hello World"}
