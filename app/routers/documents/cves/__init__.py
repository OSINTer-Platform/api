from datetime import date
from io import BytesIO
from typing import Annotated
from typing_extensions import TypedDict
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import StreamingResponse
from starlette.status import HTTP_404_NOT_FOUND

from app import config_options
from app.users.auth.dependencies import UserAuthorizer, get_source_exclusions
from app.common import HTTPError
from app.dependencies import FastapiArticleSearchQuery, FastapiCVESearchQuery
from app.utils.documents import convert_article_query_to_zip, send_file
from app.utils.pdf import MarkdownPdf
from modules.elastic import ArticleSearchQuery, CVESearchQuery
from modules.objects.articles import BaseArticle, FullArticle
from modules.objects.cves import BaseCVE, FullCVE


CVEAuthorizer = UserAuthorizer(["cve"])

router = APIRouter()
protected_router = APIRouter(
    dependencies=[Depends(CVEAuthorizer)],
)

CVEPathParam = Annotated[str, Path(pattern="^[Cc][Vv][Ee]-\\d{4}-\\d{4,7}$")]


class CVEOverview(TypedDict):
    cve: str
    title: str
    details: str


@router.get("/overview")
def get_cve_overviews(cves: Annotated[list[str], Query()]) -> list[CVEOverview]:
    cves_content = config_options.es_cve_client.query_documents(
        CVESearchQuery(limit=10000, cves=set(cves)), False
    )[0]

    cve_overviews: list[CVEOverview] = []

    for cve in cves_content:
        overview = CVEOverview(cve=cve.cve, title=cve.title, details="")

        if cve.cvss3:
            overview["details"] = " | ".join(
                [
                    f"Base: {cve.cvss3.cvss_data.base_score}",
                    f"Exploitability: {cve.cvss3.exploitability_score}",
                    f"Impact: {cve.cvss3.impact_score}",
                    f"Articles: {cve.document_count}",
                ]
            )
        elif cve.cvss2:
            overview["details"] = " | ".join(
                [
                    f"Base: {cve.cvss2.cvss_data.base_score}",
                    f"Exploitability: {cve.cvss2.exploitability_score}",
                    f"Impact: {cve.cvss2.impact_score}",
                    f"Articles: {cve.document_count}",
                ]
            )

        cve_overviews.append(overview)

    return cve_overviews


@protected_router.get(
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


@protected_router.get("/{cve_id}/articles", response_model_exclude_unset=True)
def get_cve_articles(
    cve_id: CVEPathParam, complete: Annotated[bool, Query()] = False
) -> list[BaseArticle] | list[FullArticle]:
    return config_options.es_article_client.query_documents(
        ArticleSearchQuery(
            limit=0, cve=cve_id, sort_by="publish_date", sort_order="desc"
        ),
        complete,
    )[0]


@protected_router.post("/search", response_model_by_alias=False)
def search_cves(
    query: Annotated[FastapiCVESearchQuery, Depends(FastapiCVESearchQuery)],
    complete: bool = False,
) -> list[BaseCVE] | list[FullCVE]:
    return config_options.es_cve_client.query_documents(query, complete)[0]


@protected_router.get(
    "/{cve_id}/export/md",
    tags=["download"],
    responses={
        404: {
            "model": HTTPError,
            "description": "Returned when cluster isn't found",
        }
    },
)
async def download_articles_from_cve_as_md(
    source_exclusions: Annotated[list[str], Depends(get_source_exclusions)],
    cve_id: CVEPathParam,
) -> StreamingResponse:
    zip_file: BytesIO = convert_article_query_to_zip(
        FastapiArticleSearchQuery(source_exclusions, limit=0, cve=cve_id)
    )

    return send_file(
        file_name=f"OSINTer-MD-articles-{date.today()}-CVE-{cve_id}-Download.zip",
        file_content=zip_file,
        file_type="application/zip",
    )


@protected_router.get(
    "/{cve_id}/export/pdf",
    tags=["download"],
    responses={
        404: {
            "model": HTTPError,
            "description": "Returned when cluster isn't found",
        }
    },
)
async def download_articles_from_cve_as_pdf(
    source_exclusions: Annotated[list[str], Depends(get_source_exclusions)],
    cve_id: CVEPathParam,
) -> StreamingResponse:

    articles = config_options.es_article_client.query_documents(
        FastapiArticleSearchQuery(
            source_exclusions,
            limit=0,
            cve=cve_id,
            sort_by="publish_date",
            sort_order="desc",
        ),
        True,
    )[0]

    if len(articles) < 1:
        raise HTTPException(HTTP_404_NOT_FOUND, f"No articles found for {cve_id}")

    PDFCreator = MarkdownPdf(f"{cve_id} | OSINTer")

    for article in articles:
        PDFCreator.add_article(article)

    return send_file(
        file_name=f"{cve_id}-OSINTer-{date.today()}.pdf",
        file_content=PDFCreator.save(),
        file_type="application/pdf",
    )


router.include_router(protected_router)
