from fastapi import APIRouter, Query, HTTPException

from typing import List, Dict

from modules.objects import FullArticle
from .. import config_options
from ..common import HTTPError


router = APIRouter()
article_router = APIRouter()


def mount_routers():
    if config_options.ML_AVAILABLE:
        router.include_router(article_router, prefix="/articles", tags=["articles"])


@router.get("/")
def check_ml_availability():
    return {"available": config_options.ML_AVAILABLE}


@article_router.get("/clusters", response_model=List[Dict[str, int]])
def get_article_clusters():
    clusters: Dict[int, int] = config_options.es_article_client.get_unique_values(
        "ml.cluster"
    )

    cluster_list: List[Dict[str, int]] = [
        {"cluster_id": cluster_id, "content_count": count}
        for cluster_id, count in clusters.items()
    ]

    return cluster_list


@article_router.get(
    "/cluster/{cluster_id}",
    response_model=List[FullArticle],
    response_model_exclude_unset=True,
    responses={
        404: {
            "model": HTTPError,
            "description": "Returned when cluster isn't found",
        }
    },
)
def get_articles_from_cluster(cluster_id: int, complete: bool = Query(True)):
    query = {"size": 0, "query": {"term": {"ml.cluster": {"value": cluster_id}}}}

    articles_from_cluster: List[
        FullArticle
    ] = config_options.es_article_client.query_large(query, complete)

    if not articles_from_cluster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cluster not found"
        )

    return articles_from_cluster
