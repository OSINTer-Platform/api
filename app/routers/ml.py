from fastapi import APIRouter, Query, HTTPException, Depends

from typing import List, Dict

from modules.objects import FullArticle
from modules.elastic import SearchQuery

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


def get_article_cluster_query(cluster_id: int):
    return SearchQuery(limit=0, cluster_id=cluster_id)


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
def get_articles_from_cluster(
    query: SearchQuery = Depends(get_article_cluster_query),
    complete: bool = Query(True),
):

    query.complete = complete

    articles_from_cluster: List[
        FullArticle
    ] = config_options.es_article_client.query_documents(query)["documents"]

    if not articles_from_cluster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cluster not found"
        )

    return articles_from_cluster
