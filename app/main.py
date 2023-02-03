from fastapi import FastAPI

from .routers import auth, ml
from .routers.documents import articles, tweets
from .routers.users import collections, feeds


app = FastAPI(
    servers=[
        {
            "url": "https://dev.osinter.dk/api",
            "description": "Development and Testing env",
        },
        {"url": "https://osinter.dk/api", "description": "Production env"},
    ],
    root_path="/api",
)

app.include_router(articles.router, prefix="/articles", tags=["articles"])

app.include_router(tweets.router, prefix="/tweets", tags=["tweets"])

app.include_router(auth.router, prefix="/auth", tags=["authorization"])

app.include_router(feeds.router, prefix="/my/feeds", tags=["feed"])

app.include_router(
   collections.router, prefix="/my/collections", tags=["collections"]
)

ml.mount_routers()
app.include_router(ml.router, prefix="/ml", tags=["ml"])
