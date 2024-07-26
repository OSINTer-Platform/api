from concurrent import futures
from datetime import UTC, datetime, timedelta
from typing import Any, Sequence, TypedDict, cast
from fastapi import APIRouter, HTTPException
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from app import config_options
from modules.elastic import (
    ArticleSearchQuery,
    TermAgg,
    SignificantTermAgg,
    SignificantTermAggBucket,
)
from modules.elastic.queries import CVESearchQuery, ClusterSearchQuery
from modules.objects import BaseCVE, BaseCluster, AbstractArticle

router = APIRouter()


class PartialTrendingArticle(AbstractArticle):
    title: str
    url: str
    image_url: str


class FrontpageMetrics(TypedDict):
    cves: TermAgg
    new_tags: SignificantTermAgg
    clusters: SignificantTermAgg


class TrendingArticles(TypedDict):
    articles: Sequence[PartialTrendingArticle]
    tag: str
    count: int


class FrontpageData(TypedDict):
    articles: list[TrendingArticles]
    cves: list[BaseCVE]
    clusters: list[BaseCluster]


@router.get("/frontpage", response_model_by_alias=False)
def get_front_page_metrics() -> FrontpageData:
    first_date = datetime.now(UTC) - timedelta(days=30)

    def get_articles(buckets: list[SignificantTermAggBucket]) -> list[TrendingArticles]:
        def get_articles_from_bucket(
            bucket: SignificantTermAggBucket,
        ) -> TrendingArticles:
            articles = config_options.es_article_client.query_documents(
                ArticleSearchQuery(
                    limit=6,
                    sort_by="",
                    sort_order="desc",
                    search_term=bucket["key"],
                    first_date=first_date,
                    highlight=True,
                ),
                ["title", "url", "image_url"],
            )[0]

            return {
                "tag": bucket["key"],
                "count": bucket["bg_count"] + bucket["doc_count"],
                "articles": cast(list[PartialTrendingArticle], articles),
            }

        with futures.ThreadPoolExecutor() as executor:
            article_futures = [
                executor.submit(get_articles_from_bucket, bucket) for bucket in buckets
            ]
            return [result.result() for result in futures.as_completed(article_futures)]

    def get_index(l: list[Any], el: Any) -> int:
        try:
            return l.index(el)
        except ValueError:
            return len(l) + 1

    q = ArticleSearchQuery(
        limit=1,
        first_date=first_date,
        aggregations={
            "cves": {
                "terms": {
                    "field": "tags.interesting.values",
                    "size": 10,
                    "include": "CVE.*",
                },
            },
            "new_tags": {
                "significant_terms": {
                    "field": "tags.automatic",
                    "size": 4,
                },
            },
            "clusters": {
                "significant_terms": {
                    "field": "ml.cluster",
                    "size": 10,
                    "include": "..*",
                },
            },
        },
    )

    metrics = cast(
        None | FrontpageMetrics,
        config_options.es_article_client.query_documents(q, False)[2],
    )

    if not metrics:
        raise HTTPException(
            HTTP_500_INTERNAL_SERVER_ERROR, "Error when querying metrics"
        )

    cve_ids = [bucket["key"] for bucket in metrics["cves"]["buckets"]]
    cluster_ids = [bucket["key"] for bucket in metrics["clusters"]["buckets"]]

    with futures.ThreadPoolExecutor() as executor:
        article_futures = executor.submit(get_articles, metrics["new_tags"]["buckets"])
        cve_futures = executor.submit(
            config_options.es_cve_client.query_documents,
            CVESearchQuery(cves=set(cve_ids)),
            False,
        )
        cluster_futures = executor.submit(
            config_options.es_cluster_client.query_documents,
            ClusterSearchQuery(ids=set(cluster_ids)),
            False,
        )

        trending_articles = article_futures.result()
        trending_cves = cve_futures.result()[0]
        trending_clusters = cluster_futures.result()[0]

    trending_cves.sort(key=lambda cve: get_index(cve_ids, cve.cve))
    trending_clusters.sort(key=lambda cluster: get_index(cluster_ids, cluster.id))

    return {
        "articles": trending_articles,
        "cves": trending_cves,
        "clusters": trending_clusters,
    }
