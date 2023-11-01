from datetime import date
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from modules.elastic import ArticleSearchQuery, ClusterSearchQuery
from modules.objects import (
    BaseArticle,
    BaseCluster,
    FullArticle,
    FullCluster,
)

from ... import config_options
from ...common import EsID, HTTPError
from ...utils.documents import convert_query_to_zip, send_file
from app.users.auth import require_premium

router = APIRouter(dependencies=[Depends(require_premium)])


@router.get("/clusters", response_model_exclude_unset=True)
def get_article_clusters(
    complete: bool = Query(False),
) -> list[BaseCluster] | list[FullCluster]:
    return config_options.es_cluster_client.query_documents(
        ClusterSearchQuery(limit=10000, sort_by="document_count"), complete
    )[0]


@router.get(
    "/cluster/{cluster_id}",
    responses={
        404: {
            "model": HTTPError,
            "description": "Returned when cluster isn't found",
        }
    },
)
def get_cluster(cluster_id: EsID) -> FullCluster:
    try:
        cluster = config_options.es_cluster_client.query_documents(
            ClusterSearchQuery(ids={cluster_id}), True
        )[0][0]
    except IndexError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cluster not found"
        )

    return cluster


@router.get(
    "/cluster/{cluster_id}/content",
    response_model_exclude_unset=True,
    responses={
        404: {
            "model": HTTPError,
            "description": "Returned when cluster isn't found",
        }
    },
)
def get_articles_from_cluster(
    cluster_id: EsID,
    complete: bool = Query(True),
) -> list[BaseArticle] | list[FullArticle]:
    cluster = config_options.es_cluster_client.query_documents(
        ClusterSearchQuery(ids={cluster_id}), True
    )[0][0]

    articles_from_cluster = config_options.es_article_client.query_documents(
        ArticleSearchQuery(limit=0, ids=cluster.documents, sort_by="publish_date"),
        complete,
    )[0]

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
async def download_articles_from_cluster(cluster_id: EsID) -> StreamingResponse:
    cluster = config_options.es_cluster_client.query_documents(
        ClusterSearchQuery(ids={cluster_id}), True
    )[0][0]

    zip_file: BytesIO = convert_query_to_zip(
        ArticleSearchQuery(limit=0, cluster_nr=cluster.nr)
    )

    return send_file(
        file_name=f"OSINTer-MD-articles-{date.today()}-Cluster-{cluster.nr}-Download.zip",
        file_content=zip_file,
        file_type="application/zip",
    )


