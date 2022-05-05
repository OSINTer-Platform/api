from fastapi import APIRouter, Depends, Query
from ... import config_options

from OSINTmodules.OSINTelastic import searchQuery
from OSINTmodules.OSINTobjects import FullArticle, BaseArticle
from ...dependencies import fastapiSearchQuery

from pydantic import conlist, constr
from typing import List

router = APIRouter()

@router.get("/overview/newest", response_model=List[BaseArticle])
async def get_newest_articles():
    return config_options.esArticleClient.queryDocuments(searchQuery(limit = 50, complete = False), return_object = False)["documents"]

@router.get("/overview/search", response_model=List[BaseArticle])
async def search_articles(query: fastapiSearchQuery = Depends(fastapiSearchQuery)):
    return config_options.esArticleClient.queryDocuments(query, return_object = False)["documents"]

@router.get("/content", response_model=List[FullArticle])
async def get_article_content(IDs: conlist(constr(strip_whitespace = True, min_length = 20, max_length = 20)) = Query(...)):
    return config_options.esArticleClient.queryDocuments(searchQuery(IDs = IDs, complete = True))["documents"]

@router.get("/categories", response_model=List[str])
async def get_list_of_categories():
    return config_options.esArticleClient.requestSourceCategoryListFromDB()
