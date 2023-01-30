from modules.elastic import SearchQuery

from . import config_options


def get_newest_articles():
    return config_options.es_article_client.query_documents(
        SearchQuery(limit=50, complete=False, sort_by="publish_date", sort_order="desc")
    )
