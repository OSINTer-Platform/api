from fastapi import APIRouter, Depends, Query
from typing import List
from OSINTmodules.OSINTelastic import searchQuery
from .. import config_options

router = APIRouter(
    prefix="/articles",
    responses={404: {"description": "Not found"}},
)

@router.get("/overview/newest")
async def get_newest_articles():
    return config_options.esArticleClient.queryDocuments(searchQuery(limit = 50, complete = False), return_object = False)["documents"]

@router.get("/overview/search")
async def search_articles(query: searchQuery = Depends(searchQuery)):
    return config_options.esArticleClient.queryDocuments(query, return_object = False)["documents"]

@router.get("/content")
async def get_article_content(IDs: List[str] = Query(..., length=21)):
    return config_options.esArticleClient.queryDocuments(searchQuery(IDs = IDs, complete = True))
