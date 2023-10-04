from datetime import date, datetime
from io import BytesIO
from typing import Annotated
from typing_extensions import TypedDict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import AwareDatetime

from modules.elastic import ArticleSearchQuery
from modules.objects import (
    AbstractDocument,
    BaseArticle,
    FullArticle,
    MLAttributes,
    PartialArticle,
)

from ... import config_options
from ...common import HTTPError
from ...utils.documents import convert_query_to_zip, send_file

router = APIRouter()


def get_article_cluster_query(cluster_id: int) -> ArticleSearchQuery:
    return ArticleSearchQuery(limit=0, cluster_id=cluster_id)


class ClusterListItem(TypedDict):
    cluster_id: int
    content_count: int


@router.get("/clusters")
def get_article_clusters() -> list[ClusterListItem]:
    clusters: dict[str, int] = config_options.es_article_client.get_unique_values(
        "ml.cluster"
    )

    cluster_list: list[ClusterListItem] = [
        {"cluster_id": int(cluster_id), "content_count": count}
        for cluster_id, count in clusters.items()
    ]

    return cluster_list


@router.get(
    "/cluster/{cluster_id}",
    response_model_exclude_unset=True,
    response_model=list[FullArticle],
    responses={
        404: {
            "model": HTTPError,
            "description": "Returned when cluster isn't found",
        }
    },
)
def get_articles_from_cluster(
    query: ArticleSearchQuery = Depends(get_article_cluster_query),
    complete: bool = Query(True),
) -> list[BaseArticle] | list[FullArticle]:
    articles_from_cluster: list[BaseArticle] | list[
        FullArticle
    ] = config_options.es_article_client.query_documents(query, complete)[0]

    if not articles_from_cluster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cluster not found"
        )

    return articles_from_cluster


@router.get(
    "/cluster/{cluster_id}/export",
    tags=["download"],
    responses={
        404: {
            "model": HTTPError,
            "description": "Returned when cluster isn't found",
        }
    },
)
async def download_articles_from_cluster(
    query: ArticleSearchQuery = Depends(get_article_cluster_query),
) -> StreamingResponse:
    zip_file: BytesIO = convert_query_to_zip(query)

    return send_file(
        file_name=f"OSINTer-MD-articles-{date.today()}-Cluster-{query.cluster_id}-Download.zip",
        file_content=zip_file,
        file_type="application/zip",
    )


class PartialMLArticle(AbstractDocument):
    title: str
    description: str
    source: str
    profile: str
    publish_date: Annotated[datetime, AwareDatetime]
    ml: MLAttributes


@router.get(
    "/map/partial",
    response_model=list[PartialMLArticle],
    response_model_exclude_none=True,
)
async def query_partial_article_map() -> list[PartialArticle]:
    articles = config_options.es_article_client.query_documents(
        ArticleSearchQuery(limit=0),
        ["title", "description", "source", "profile", "publish_date", "ml"],
    )[0]

    return articles


@router.get("/map/full")
async def query_full_article_map() -> list[FullArticle]:
    return config_options.es_article_client.query_all_documents()
