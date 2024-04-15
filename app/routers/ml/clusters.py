from datetime import date
from io import BytesIO
from typing import Annotated, TypeAlias, Union

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.authorization import UserAuthorizer, get_allowed_areas
from app.users.schemas import User
from modules.elastic import ClusterSearchQuery
from modules.objects import (
    BaseArticle,
    BaseCluster,
    FullArticle,
    FullCluster,
)

from ... import config_options
from ...common import EsID, HTTPError
from ...utils.documents import convert_article_query_to_zip, send_file
from app.dependencies import FastapiArticleSearchQuery
from app.authorization import get_source_exclusions

ClusterAuthorizer = UserAuthorizer(["cluster"])
router = APIRouter()

ClusterID: TypeAlias = Union[int, EsID]


def query_cluster(cluster_id: ClusterID) -> FullCluster:
    try:
        if isinstance(cluster_id, int):
            return config_options.es_cluster_client.query_documents(
                ClusterSearchQuery(cluster_nr=cluster_id), True
            )[0][0]
        elif isinstance(cluster_id, str):
            return config_options.es_cluster_client.query_documents(
                ClusterSearchQuery(ids={cluster_id}), True
            )[0][0]
        else:
            raise NotImplemented
    except IndexError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cluster not found"
        )


@router.get(
    "/clusters",
    response_model_exclude_unset=True,
    dependencies=[Depends(ClusterAuthorizer)],
)
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
    dependencies=[Depends(ClusterAuthorizer)],
)
def get_cluster(cluster: FullCluster = Depends(query_cluster)) -> FullCluster:
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
    user: Annotated[User, Depends(UserAuthorizer(["cluster"]))],
    cluster: FullCluster = Depends(query_cluster),
    complete: bool = Query(True),
) -> list[BaseArticle] | list[FullArticle]:
    source_exclusions = get_source_exclusions(get_allowed_areas(user))

    articles_from_cluster = config_options.es_article_client.query_documents(
        FastapiArticleSearchQuery(
            source_exclusions, limit=0, ids=cluster.documents, sort_by="publish_date"
        ),
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
async def download_articles_from_cluster(
    user: Annotated[User, Depends(UserAuthorizer(["cluster"]))],
    cluster: FullCluster = Depends(query_cluster),
) -> StreamingResponse:
    source_exclusions = get_source_exclusions(get_allowed_areas(user))

    zip_file: BytesIO = convert_article_query_to_zip(
        FastapiArticleSearchQuery(source_exclusions, limit=0, cluster_id=cluster.id)
    )

    return send_file(
        file_name=f"OSINTer-MD-articles-{date.today()}-Cluster-{cluster.nr}-Download.zip",
        file_content=zip_file,
        file_type="application/zip",
    )
