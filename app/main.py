from fastapi import FastAPI, Depends, Request
from .routers import documents

from . import config_options

from OSINTmodules.OSINTelastic import elasticDB

# Wrapper class used to pass the right es client to each mount of the documents router using dependency injection and the request state
class es_client_getter():
    def __init__(self, es_client_name: str):
        self.es_client = config_options[es_client_name]

    def __call__(self, request : Request):
        request.state.es_client = self.es_client

app = FastAPI()

app.include_router(
        documents.router,
        prefix = "/tweets",
        tags=["tweets", "documents"],
        dependencies = [Depends(es_client_getter("esTweetClient"))]
    )

app.include_router(
        documents.router,
        prefix = "/articles",
        tags=["articles", "documents"],
        dependencies = [Depends(es_client_getter("esArticleClient"))]
    )

@app.get("/")
async def root():
    return {"message": "Hello World"}
