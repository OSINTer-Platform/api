from datetime import date
from io import BytesIO
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from modules.elastic import SearchQuery
from modules.files import convert_article_to_md
from modules.objects import BaseArticle, FullArticle
from modules.profiles import collect_website_details

from .... import config_options
from ....common import EsID, EsIDList, HTTPError
from ....dependencies import FastapiSearchQuery
from ....utils.documents import convert_ids_to_zip, convert_query_to_zip, send_file
from .rss import router as rss_router
from .utils import get_newest_articles

router = APIRouter()
router.include_router(rss_router, tags=["rss"])

router.get("/newest", response_model=List[BaseArticle])(get_newest_articles)


@router.get(
    "/search",
    response_model=List[FullArticle],
    response_model_exclude_unset=True,
)
async def search_articles(query: FastapiSearchQuery = Depends(FastapiSearchQuery)):
    articles = config_options.es_article_client.query_documents(query)
    return articles


@router.get("/content", response_model=List[FullArticle])
async def get_article_content(ids: EsIDList = Query(...)):
    for id in ids:
        config_options.es_article_client.increment_read_counter(id)

    return config_options.es_article_client.query_documents(
        SearchQuery(ids=ids, complete=True)
    )


@router.get("/categories", response_model=Dict[str, Dict[str, str]])
async def get_list_of_categories():
    return collect_website_details(config_options.es_article_client)


# Has to be defined above route for download_single_markdown_file, as it will otherwise collide due to the part of the route "multiple" can be interpreted as an ID
@router.get(
    "/export/multiple",
    tags=["download"],
    responses={
        404: {
            "model": HTTPError,
            "description": "Returned when no of the requested article exist",
        }
    },
)
def download_multiple_markdown_files_using_ids(
    zip_file: BytesIO = Depends(convert_ids_to_zip),
):
    return send_file(
        file_name=f"OSINTer-MD-articles-{date.today()}-ID-Download.zip",
        file_content=zip_file,
        file_type="application/zip",
    )


@router.get(
    "/export/search",
    tags=["download"],
    responses={
        404: {
            "model": HTTPError,
            "description": "Returned when query matches no articles",
        }
    },
)
def download_multiple_markdown_files_using_search(
    zip_file: BytesIO = Depends(convert_query_to_zip),
):
    return send_file(
        file_name=f"OSINTer-MD-articles-{date.today()}-Search-Download.zip",
        file_content=zip_file,
        file_type="application/zip",
    )


@router.get(
    "/export/{id}",
    tags=["download"],
    responses={
        404: {
            "model": HTTPError,
            "description": "Returned when requested article doesn't exist",
        }
    },
)
def download_single_markdown_file(id: EsID):
    article = config_options.es_article_client.query_documents(
        SearchQuery(limit=1, ids=[id], complete=True)
    )[0]

    if article != []:
        article_file = convert_article_to_md(article)

        return send_file(
            file_name=f"{article.title.replace(' ', '-')}.md",
            file_content=article_file,
            file_type="text/markdown",
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Article not found"
        )
