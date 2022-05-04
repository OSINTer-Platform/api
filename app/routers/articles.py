from fastapi import APIRouter, Depends, Query
from .. import config_options

from OSINTmodules.OSINTelastic import searchQuery
from ..dependencies import fastapiSearchQuery

from pydantic import conlist, constr

router = APIRouter(
    prefix="/articles",
    responses={404: {"description": "Not found"}},
)

@router.get("/overview/newest")
async def get_newest_articles():
    return config_options.esArticleClient.queryDocuments(searchQuery(limit = 50, complete = False), return_object = False)["documents"]

@router.get("/overview/search")
async def search_articles(query: fastapiSearchQuery = Depends(fastapiSearchQuery)):
    return config_options.esArticleClient.queryDocuments(query, return_object = False)["documents"]

@router.get("/content")
async def get_article_content(IDs: conlist(constr(strip_whitespace = True, min_length = 20, max_length = 20)) = Query(...)):
    return config_options.esArticleClient.queryDocuments(searchQuery(IDs = IDs, complete = True))

@router.get("/categories")
async def get_list_of_categories():
    return config_options.esArticleClient.requestSourceCategoryListFromDB()
