from typing import cast
from fastapi import APIRouter, Depends, Query

from app.common import EsID
from modules.elastic import SearchQuery
from modules.objects import FullTweet

from ... import config_options
from ...dependencies import FastapiSearchQuery

router = APIRouter()


@router.get("/overview/newest", response_model=list[FullTweet])
async def get_newest_articles():
    return config_options.es_tweet_client.query_documents(
        SearchQuery(limit=50, complete=True)
    )


@router.get(
    "/overview/search",
    response_model=list[FullTweet],
    response_model_exclude_unset=True,
)
async def search_articles(query: FastapiSearchQuery = Depends(FastapiSearchQuery)):
    return config_options.es_tweet_client.query_documents(query)


@router.get("/content", response_model=list[FullTweet])
async def get_article_content(ids: list[EsID] = Query(...)):
    return config_options.es_tweet_client.query_documents(
        SearchQuery(ids=cast(list[str], ids), complete=True)
    )


@router.get("/categories", response_model=list[str])
async def get_list_of_categories():
    return config_options.es_tweet_client.get_unique_values()
