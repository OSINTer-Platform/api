from fastapi import APIRouter, Depends, Query

from app.common import EsIDList
from modules.elastic import SearchQuery
from modules.objects import BaseTweet, FullTweet

from ... import config_options
from ...dependencies import FastapiSearchQuery

router = APIRouter()


@router.get("/overview/newest", response_model=list[BaseTweet])
async def get_newest_articles():
    return config_options.es_tweet_client.query_documents(
        SearchQuery(limit=50, complete=False)
    )


@router.get(
    "/overview/search",
    response_model=list[FullTweet],
    response_model_exclude_unset=True,
)
async def search_articles(query: FastapiSearchQuery = Depends(FastapiSearchQuery)):
    return config_options.es_tweet_client.query_documents(query)


@router.get("/content", response_model=list[FullTweet])
async def get_article_content(ids: EsIDList = Query(...)):
    return config_options.es_tweet_client.query_documents(
        SearchQuery(ids=ids, complete=True)
    )


@router.get("/categories", response_model=list[str])
async def get_list_of_categories():
    return config_options.es_tweet_client.get_unique_values()
