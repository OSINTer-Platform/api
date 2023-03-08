from fastapi import FastAPI

from .routers import auth, ml
from .routers.documents import articles, tweets
from .routers.subscriptions import feeds, collections
from .routers import user_items

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    root_path="/",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(articles.router, prefix="/articles", tags=["articles"])

app.include_router(tweets.router, prefix="/tweets", tags=["tweets"])

app.include_router(auth.router, prefix="/auth", tags=["authorization"])

app.include_router(feeds.router, prefix="/my/feeds", tags=["feed"])

app.include_router(collections.router, prefix="/my/collections", tags=["collections"])

app.include_router(user_items.router, prefix="/user-items", tags=["user-items"])

ml.mount_routers()
app.include_router(ml.router, prefix="/ml", tags=["ml"])
