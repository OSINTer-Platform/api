from modules.elastic import ArticleSearchQuery
from modules.objects import BaseArticle

from .... import config_options


def get_newest_articles() -> list[BaseArticle]:
    return config_options.es_article_client.query_documents(
        ArticleSearchQuery(limit=50, sort_by="publish_date", sort_order="desc")
    )
