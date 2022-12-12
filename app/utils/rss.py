from datetime import datetime
from fastapi_rss import (
    RSSResponse,
    RSSFeed,
    Item as RSSItem,
    Source as RSSSource,
    SourceAttrs as RSSSourceAttrs,
)

from .. import config_options

from modules.objects import BaseArticle
from modules.profiles import collect_website_details 

from typing import Optional

def generate_rss_item(
    article: BaseArticle, source_details: Optional[dict[str, dict[str, str]]] = None
) -> RSSItem:
    item: RSSItem = RSSItem(
        title=article.title,
        link=article.url,
        description=article.description,
        pub_date=article.publish_date,
    )

    if source_details:
        if article.profile == "cybernews":
            print(article)
        item.source = RSSSource(
            content=source_details[article.profile]["name"],
            attrs=RSSSourceAttrs(url=source_details[article.profile]["url"]),
        )

    return item

def generate_rss_feed(articles: list[BaseArticle]) -> RSSFeed:
    feed: RSSFeed = RSSFeed(
        title="OSINTer",
        link="https://osinter.dk",
        description="OSINTer is in short a framework, or online platform, which aims to automate the heavy-lifting for CTI specialists. In other words, it's a set of open-source tools which can help the trend researchers within cybersecurity spot new trends within the current cyberspace - with a special focus on current threats - and thereby help companies, organisation or individuals tackle the cyberattacks of tomorrow.OSINTer is in short a framework, or online platform, which aims to automate the heavy-lifting for CTI specialists. In other words, it's a set of open-source tools which can help the trend researchers within cybersecurity spot new trends within the current cyberspace - with a special focus on current threats - and thereby help companies, organisation or individuals tackle the cyberattacks of tomorrow.",
        language="en_US",
        pub_date=datetime.now(),
    )

    source_details: dict[str, dict[str, str]] = collect_website_details(config_options.es_article_client)

    for article in articles:
        feed.item.append(generate_rss_item(article, source_details))

    return feed

def generate_rss_response(articles: list[BaseArticle]) -> RSSResponse:
    return RSSResponse(generate_rss_feed(articles))
