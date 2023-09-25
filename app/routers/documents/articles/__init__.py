from datetime import date
from io import BytesIO
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pathvalidate import sanitize_filename
from app.users.auth import get_full_user, get_username_from_token, oauth2_scheme
from app.users.crud import modify_collection
from app.utils.profiles import ProfileDetails, collect_profile_details

from modules.elastic import ArticleSearchQuery
from modules.files import article_to_md
from modules.objects import BaseArticle, FullArticle

from .... import config_options
from ....common import EsID, HTTPError
from ....dependencies import FastapiArticleSearchQuery
from ....utils.documents import convert_query_to_zip, send_file
from .rss import router as rss_router

router = APIRouter()
router.include_router(rss_router, tags=["rss"])


@router.get("/newest")
async def get_newest_articles() -> list[BaseArticle]:
    return config_options.es_article_client.query_documents(
        ArticleSearchQuery(limit=50, sort_by="publish_date", sort_order="desc"), False
    )[0]


@router.get("/search", response_model_exclude_unset=True)
async def search_articles(
    query: FastapiArticleSearchQuery = Depends(FastapiArticleSearchQuery),
    complete: bool = Query(False),
) -> list[BaseArticle] | list[FullArticle]:
    articles = config_options.es_article_client.query_documents(query, complete)[0]
    return articles


@router.get(
    "/search/export",
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
) -> StreamingResponse:
    return send_file(
        file_name=f"OSINTer-MD-articles-{date.today()}-Search-Download.zip",
        file_content=zip_file,
        file_type="application/zip",
    )


@router.get("/categories")
async def get_list_of_categories() -> dict[str, ProfileDetails]:
    return collect_profile_details()


articleNotFound: dict[str | int, dict[str, Any]] = {
    404: {
        "model": HTTPError,
        "description": "Returned when the requested article doesn't exist",
    }
}


def get_single_article(id: EsID) -> FullArticle:
    try:
        return config_options.es_article_client.query_documents(
            ArticleSearchQuery(limit=1, ids={id}), True
        )[0][0]
    except IndexError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Article not found"
        )


@router.get("/{id}/export", tags=["download"], responses=articleNotFound)
def download_single_markdown_file(
    article: FullArticle = Depends(get_single_article),
) -> StreamingResponse:
    article_file = article_to_md(article)

    return send_file(
        file_name=f"{sanitize_filename(article.title)}.md",
        file_content=article_file,
        file_type="text/markdown",
    )


@router.get(
    "/{id}/content",
    responses={
        404: {
            "model": HTTPError,
            "description": "Returned when requested article doesn't exist",
        }
    },
)
async def get_article_content(id: EsID, request: Request) -> FullArticle:
    article = get_single_article(id)

    config_options.es_article_client.increment_read_counter(id)

    try:
        token = await oauth2_scheme(request)

        if token:
            user = get_full_user(await get_username_from_token(token))
            if user.already_read:
                modify_collection(user.already_read, set([id]), user, "extend")

    except HTTPException:
        pass

    return article


@router.get("/{id}/similar")
async def get_similar_articles(
    article: FullArticle = Depends(get_single_article),
) -> list[BaseArticle]:
    if len(article.similar) == 0:
        return []

    articles = config_options.es_article_client.query_documents(
        ArticleSearchQuery(
            limit=10_000,
            ids=set(article.similar),
        ),
        False,
    )[0]

    # The similar articles id list is sorted so that the closest is the first
    # So the list has to be manually sorted as Elasticsearch will scramble it
    return sorted(articles, key=lambda a: article.similar.index(a.id))
