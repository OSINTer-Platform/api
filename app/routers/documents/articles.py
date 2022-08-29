from fastapi import APIRouter, Depends, Query, HTTPException, status

from ... import config_options

from modules.elastic import SearchQuery
from modules.files import convert_article_to_md
from modules.objects import FullArticle, BaseArticle
from modules.profiles import collect_website_details

from ...utils.documents import convert_ids_to_zip, convert_query_to_zip, send_file
from ...dependencies import FastapiSearchQuery
from ...common import HTTPError

from pydantic import conlist, constr
from typing import List, Dict

from io import BytesIO
from datetime import date

router = APIRouter()


@router.get("/overview/newest", response_model=List[BaseArticle])
async def get_newest_articles():
    return config_options.es_article_client.query_documents(
        SearchQuery(limit=50, complete=False)
    )["documents"]


@router.get(
    "/overview/search",
    response_model=List[FullArticle],
    response_model_exclude_unset=True,
)
async def search_articles(query: FastapiSearchQuery = Depends(FastapiSearchQuery)):
    articles = config_options.es_article_client.query_documents(query)["documents"]
    return articles


@router.get("/content", response_model=List[FullArticle])
async def get_article_content(
    ids: conlist(constr(strip_whitespace=True, min_length=20, max_length=20)) = Query(
        ...
    )
):
    for id in ids:
        config_options.es_article_client.increment_read_counter(id)

    return config_options.es_article_client.query_documents(
        SearchQuery(ids=ids, complete=True)
    )["documents"]


@router.get("/categories", response_model=Dict[str, Dict[str, str]])
async def get_list_of_categories():
    return collect_website_details(config_options.es_article_client)


@router.get(
    "/download/MD/single",
    tags=["download"],
    responses={
        404: {
            "model": HTTPError,
            "description": "Returned requested article doesn't exist",
        }
    },
)
def download_single_markdown_file(
    id: constr(strip_whitespace=True, min_length=20, max_length=20) = Query(...)
):
    article = config_options.es_article_client.query_documents(
        SearchQuery(limit=1, ids=[id], complete=True)
    )["documents"][0]

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


@router.get(
    "/download/MD/multiple/ID",
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
    "/download/MD/multiple/search",
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
