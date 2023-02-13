from collections.abc import Sequence
from datetime import date
from io import BytesIO
from typing import TypedDict

from fastapi import APIRouter, Depends, HTTPException, Query, status

from modules.elastic import SearchQuery
from modules.objects import FullArticle

from .. import config_options
from ..common import HTTPError
from ..utils.documents import convert_query_to_zip, send_file

router = APIRouter()
article_router = APIRouter()


def mount_routers():
    if config_options.ML_AVAILABLE:
        router.include_router(article_router, prefix="/articles", tags=["articles"])


@router.get("/")
def check_ml_availability():
    return {"available": config_options.ML_AVAILABLE}


def get_article_cluster_query(cluster_id: int):
    return SearchQuery(limit=0, cluster_id=cluster_id)


class ClusterListItem(TypedDict):
    cluster_id: str
    content_count: int


@article_router.get("/clusters", response_model=list[ClusterListItem])
def get_article_clusters():
    clusters: dict[str, int] = config_options.es_article_client.get_unique_values(
        "ml.cluster"
    )

    cluster_list: list[ClusterListItem] = [
        {"cluster_id": cluster_id, "content_count": count}
        for cluster_id, count in clusters.items()
    ]

    return cluster_list


@article_router.get(
    "/cluster/{cluster_id}",
    response_model=list[FullArticle],
    response_model_exclude_unset=True,
    responses={
        404: {
            "model": HTTPError,
            "description": "Returned when cluster isn't found",
        }
    },
)
def get_articles_from_cluster(
    query: SearchQuery = Depends(get_article_cluster_query),
    complete: bool = Query(True),
):

    query.complete = complete

    articles_from_cluster: Sequence[
        FullArticle
    ] = config_options.es_article_client.query_documents(query)

    if not articles_from_cluster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cluster not found"
        )

    return articles_from_cluster


@article_router.get(
    "/cluster/{cluster_id}/export",
    tags=["download"],
    responses={
        404: {
            "model": HTTPError,
            "description": "Returned when cluster isn't found",
        }
    },
)
async def download_articles_from_cluster(cluster_id: int):
    query = get_article_cluster_query(cluster_id)
    zip_file: BytesIO = convert_query_to_zip(query)

    return send_file(
        file_name=f"OSINTer-MD-articles-{date.today()}-Cluster-{cluster_id}-Download.zip",
        file_content=zip_file,
        file_type="application/zip",
    )
