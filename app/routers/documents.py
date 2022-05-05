from fastapi import APIRouter, Depends, Query, Request

from OSINTmodules.OSINTelastic import searchQuery
from ..dependencies import fastapiSearchQuery

from pydantic import conlist, constr

router = APIRouter()

@router.get("/overview/newest")
async def get_newest_documents(request : Request):
    return request.state.es_client.queryDocuments(searchQuery(limit = 50, complete = False), return_object = False)["documents"]

@router.get("/overview/search")
async def search_documents(request : Request, query: fastapiSearchQuery = Depends(fastapiSearchQuery)):
    return request.state.es_client.queryDocuments(query, return_object = False)["documents"]

@router.get("/content")
async def get_document_content(request : Request, IDs: conlist(constr(strip_whitespace = True, min_length = 20, max_length = 20)) = Query(...)):
    return request.state.es_client.queryDocuments(searchQuery(IDs = IDs, complete = True))

@router.get("/categories")
async def get_list_of_categories(request : Request):
    return request.state.es_client.requestSourceCategoryListFromDB()
