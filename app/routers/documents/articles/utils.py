from modules.elastic import SearchQuery
from modules.objects import BaseArticle

from .... import config_options


def get_newest_articles() -> list[BaseArticle]:
    return config_options.es_article_client.query_documents(
        SearchQuery(limit=50, complete=False, sort_by="publish_date", sort_order="desc")
    )
