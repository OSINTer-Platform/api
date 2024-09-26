from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import AwareDatetime

from modules.objects import (
    AbstractDocument,
    FullArticle,
    MLAttributes,
    PartialArticle,
)

from ... import config_options

from app.dependencies import FastapiArticleSearchQuery
from app.users.auth.authorization import UserAuthorizer

MapAuthorizer = UserAuthorizer(["map"])

router = APIRouter(prefix="/map", dependencies=[Depends(MapAuthorizer)])


class PartialMLArticle(AbstractDocument):
    title: str
    description: str
    source: str
    profile: str
    publish_date: Annotated[datetime, AwareDatetime]
    ml: MLAttributes


@router.get(
    "/partial",
    response_model=list[PartialMLArticle],
    response_model_exclude_none=True,
)
async def query_partial_article_map() -> list[PartialArticle]:
    articles = config_options.es_article_client.query_documents(
        FastapiArticleSearchQuery([], limit=0),
        ["title", "description", "source", "profile", "publish_date", "ml"],
    )[0]

    return articles


@router.get("/full")
async def query_full_article_map() -> list[FullArticle]:
    return config_options.es_article_client.query_all_documents()
