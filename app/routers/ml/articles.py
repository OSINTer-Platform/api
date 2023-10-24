from datetime import date, datetime
from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import AwareDatetime

from modules.elastic import ArticleSearchQuery, ClusterSearchQuery
from modules.objects import (
    AbstractDocument,
    BaseArticle,
    BaseCluster,
    FullArticle,
    FullCluster,
    MLAttributes,
    PartialArticle,
)

from ... import config_options
from ...common import HTTPError
from ...utils.documents import convert_query_to_zip, send_file

router = APIRouter()


@router.get("/clusters", response_model_exclude_unset=True)
def get_article_clusters(
    complete: bool = Query(False),
) -> list[BaseCluster] | list[FullCluster]:
    return config_options.es_cluster_client.query_documents(
        ClusterSearchQuery(limit=10000, sort_by="document_count"), complete
    )[0]


@router.get(
    "/cluster/{cluster_nr}",
    responses={
        404: {
            "model": HTTPError,
            "description": "Returned when cluster isn't found",
        }
    },
)
def get_cluster(cluster_nr: int) -> FullCluster:
    cluster = config_options.es_cluster_client.query_documents(
        ClusterSearchQuery(cluster_nr=cluster_nr), True
    )[0]

    if not cluster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cluster not found"
        )

    return cluster[0]


@router.get(
    "/cluster/{cluster_nr}/content",
    response_model_exclude_unset=True,
    responses={
        404: {
            "model": HTTPError,
            "description": "Returned when cluster isn't found",
        }
    },
)
def get_articles_from_cluster(
    cluster_nr: int,
    complete: bool = Query(True),
) -> list[BaseArticle] | list[FullArticle]:
    articles_from_cluster = config_options.es_article_client.query_documents(
        ArticleSearchQuery(limit=0, cluster_nr=cluster_nr), complete
    )[0]

    if not articles_from_cluster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cluster not found"
        )

    return articles_from_cluster


@router.get(
    "/cluster/{cluster_nr}/export",
    tags=["download"],
    responses={
        404: {
            "model": HTTPError,
            "description": "Returned when cluster isn't found",
        }
    },
)
async def download_articles_from_cluster(cluster_nr: int) -> StreamingResponse:
    zip_file: BytesIO = convert_query_to_zip(
        ArticleSearchQuery(limit=0, cluster_nr=cluster_nr)
    )

    return send_file(
        file_name=f"OSINTer-MD-articles-{date.today()}-Cluster-{cluster_nr}-Download.zip",
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
