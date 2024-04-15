from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from starlette.status import HTTP_404_NOT_FOUND

from app import config_options
from app.dependencies import FastapiCVESearchQuery
from app.common import HTTPError
from modules.elastic import ArticleSearchQuery, CVESearchQuery
from modules.objects.articles import BaseArticle, FullArticle
from modules.objects.cves import BaseCVE, FullCVE


router = APIRouter()

CVEPathParam = Annotated[str, Path(pattern="^[Cc][Vv][Ee]-\\d{4}-\\d{4,7}$")]


@router.get(
    "/{cve_id}",
    response_model_exclude_unset=True,
    response_model_by_alias=False,
    responses={
        404: {
            "model": HTTPError,
            "description": "Returned when CVE isn't found",
        }
    },
)
def get_cve_details(
    cve_id: CVEPathParam, complete: Annotated[bool, Query()] = False
) -> BaseCVE | FullCVE:
    try:
        cve = config_options.es_cve_client.query_documents(
            CVESearchQuery(limit=1, cves={cve_id.upper()}), complete
        )[0][0]
        return cve
    except IndexError:
        raise HTTPException(HTTP_404_NOT_FOUND, "CVE was not found")


@router.get("/{cve_id}/articles", response_model_exclude_unset=True)
def get_cve_articles(
    cve_id: CVEPathParam, complete: Annotated[bool, Query()] = False
) -> list[BaseArticle] | list[FullArticle]:
    return config_options.es_article_client.query_documents(
        ArticleSearchQuery(limit=0, cve=cve_id), complete
    )[0]


@router.post("/search")
def search_cves(
    query: Annotated[FastapiCVESearchQuery, Depends(FastapiCVESearchQuery)],
    complete: bool = False,
) -> list[BaseCVE] | list[FullCVE]:
    return config_options.es_cve_client.query_documents(query, complete)[0]
