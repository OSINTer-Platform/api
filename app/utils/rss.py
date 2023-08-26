from collections.abc import Sequence
from datetime import datetime

from fastapi_rss import (
    Item as RSSItem,
    RSSFeed,
    RSSResponse,
    Source as RSSSource,
    SourceAttrs as RSSSourceAttrs,
)
from app.utils.profiles import ProfileDetails, collect_profile_details

from modules.objects import BaseArticle


def generate_rss_item(
    article: BaseArticle, source_details: dict[str, ProfileDetails] | None = None
) -> RSSItem:
    item: RSSItem = RSSItem(
        title=article.title,
        link=article.url,
        description=article.description,
        pub_date=article.publish_date,
    )  # pyright: ignore

    if source_details:
        item.source = RSSSource(
            content=source_details[article.profile]["name"],
            attrs=RSSSourceAttrs(url=source_details[article.profile]["url"]),
        )

    return item


def generate_rss_feed(articles: Sequence[BaseArticle]) -> RSSFeed:
    feed: RSSFeed = RSSFeed(
        title="OSINTer",
        link="https://osinter.dk",
        description="OSINTer is in short a framework, or online platform, which aims to automate the heavy-lifting for CTI specialists. In other words, it's a set of open-source tools which can help the trend researchers within cybersecurity spot new trends within the current cyberspace - with a special focus on current threats - and thereby help companies, organisation or individuals tackle the cyberattacks of tomorrow.OSINTer is in short a framework, or online platform, which aims to automate the heavy-lifting for CTI specialists. In other words, it's a set of open-source tools which can help the trend researchers within cybersecurity spot new trends within the current cyberspace - with a special focus on current threats - and thereby help companies, organisation or individuals tackle the cyberattacks of tomorrow.",
        language="en_US",
        pub_date=datetime.now(),
    )  # pyright: ignore

    source_details: dict[str, ProfileDetails] = collect_profile_details()

    for article in articles:
        feed.item.append(generate_rss_item(article, source_details))

    return feed


def generate_rss_response(articles: Sequence[BaseArticle]) -> RSSResponse:
    return RSSResponse(generate_rss_feed(articles))
