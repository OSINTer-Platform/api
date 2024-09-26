from datetime import date
from io import BytesIO
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pathvalidate import sanitize_filename

from app.authorization import UserAuthorizer, get_allowed_areas
from app.users.auth import (
    get_user_from_request,
)
from app.users.crud import modify_collection, update_user
from app.users.schemas import User
from app.utils.profiles import ProfileDetails, collect_profile_details

from modules.files import article_to_md
from modules.objects import BaseArticle, FullArticle

from .... import config_options
from ....common import EsID, HTTPError
from ....dependencies import (
    FastapiArticleSearchQuery,
    SourceExclusions,
)
from app.authorization import get_source_exclusions
from ....utils.documents import convert_article_query_to_zip, send_file
from .rss import router as rss_router

ArticleAuthorizer = UserAuthorizer(["articles"])

router = APIRouter(dependencies=[Depends(ArticleAuthorizer)])
router.include_router(rss_router, tags=["rss"])


@router.get("/newest")
async def get_newest_articles(source_exclusions: SourceExclusions) -> list[BaseArticle]:
    return config_options.es_article_client.query_documents(
        FastapiArticleSearchQuery(
            source_exclusions, limit=50, sort_by="publish_date", sort_order="desc"
        ),
        False,
    )[0]


@router.post("/search", response_model_exclude_unset=True)
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
    zip_file: BytesIO = Depends(convert_article_query_to_zip),
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


def get_single_article(id: EsID, source_exclusions: SourceExclusions) -> FullArticle:
    try:
        return config_options.es_article_client.query_documents(
            FastapiArticleSearchQuery(source_exclusions, limit=1, ids={id}), True
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


def mark_as_read(article: FullArticle, user: User | None) -> None:
    config_options.es_article_client.increment_read_counter(article.id)
    if user:
        user.read_articles = [id for id in user.read_articles if id != article.id]
        user.read_articles.insert(0, article.id)
        update_user(user)


@router.get(
    "/{id}/content",
    responses={
        404: {
            "model": HTTPError,
            "description": "Returned when requested article doesn't exist",
        }
    },
)
async def get_article_content(
    background_tasks: BackgroundTasks,
    id: EsID,
    user: User | None = Depends(get_user_from_request),
) -> FullArticle:
    source_exclusions = get_source_exclusions(get_allowed_areas(user))
    article = get_single_article(id, source_exclusions)

    background_tasks.add_task(mark_as_read, article, user)

    return article


@router.get("/{id}/similar")
async def get_similar_articles(
    id: EsID, user: Annotated[User, Depends(UserAuthorizer(["similar"]))]
) -> list[BaseArticle]:
    source_exclusions = get_source_exclusions(get_allowed_areas(user))
    article = get_single_article(id, source_exclusions)

    if len(article.similar) == 0:
        return []

    articles = config_options.es_article_client.query_documents(
        FastapiArticleSearchQuery(
            source_exclusions, limit=10_000, ids=set(article.similar)
        ),
        False,
    )[0]

    # The similar articles id list is sorted so that the closest is the first
    # So the list has to be manually sorted as Elasticsearch will scramble it
    return sorted(articles, key=lambda a: article.similar.index(a.id))
