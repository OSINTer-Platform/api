from fastapi import APIRouter, Depends, Query
from ... import config_options

from modules.elastic import SearchQuery
from modules.objects import FullTweet, BaseTweet
from ...dependencies import FastapiSearchQuery

from pydantic import conlist, constr
from typing import List

router = APIRouter()


@router.get("/overview/newest", response_model=List[BaseTweet])
async def get_newest_articles():
    return config_options.es_tweet_client.query_documents(
        SearchQuery(limit=50, complete=False)
    )["documents"]


@router.get(
    "/overview/search",
    response_model=List[FullTweet],
    response_model_exclude_unset=True,
)
async def search_articles(query: FastapiSearchQuery = Depends(FastapiSearchQuery)):
    return config_options.es_tweet_client.query_documents(query)["documents"]


@router.get("/content", response_model=List[FullTweet])
async def get_article_content(
    ids: conlist(constr(strip_whitespace=True, min_length=20, max_length=20)) = Query(
        ...
    )
):
    return config_options.es_tweet_client.query_documents(
        SearchQuery(ids=ids, complete=True)
    )["documents"]


@router.get("/categories", response_model=List[str])
async def get_list_of_categories():
    return config_options.es_tweet_client.get_unique_values()
