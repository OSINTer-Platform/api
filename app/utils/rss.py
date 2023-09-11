from collections.abc import Sequence
from datetime import datetime
from typing import Annotated

from pydantic import AwareDatetime, BaseModel

from app.utils.profiles import ProfileDetails, collect_profile_details

from app import config_options

from modules.objects import FullArticle


class RSSGUID(BaseModel):
    content: str
    is_permalink: bool


class RSSSource(BaseModel):
    name: str
    url: str


class RSSItem(BaseModel):
    guid: RSSGUID

    link: str
    title: str
    description: str
    image: str
    author: str | None = None

    pub_date: Annotated[datetime, AwareDatetime]
    source: RSSSource | None = None


class RSSFeed(BaseModel):
    title: str
    description: str
    image_url: str
    language: str
    link: str

    managing_editor: str | None = None
    webmaster: str | None = None

    copyright: str | None = None

    pub_date: Annotated[datetime, AwareDatetime]
    last_build_date: Annotated[datetime, AwareDatetime]

    items: list[RSSItem]


def generate_rss_item(
    article: FullArticle,
    original_url: bool,
    source_details: dict[str, ProfileDetails] | None = None,
) -> RSSItem:
    url = (
        article.url
        if original_url
        else f"{config_options.ARTICLE_RENDER_URL}/{article.id}"
    )
    item: RSSItem = RSSItem(
        guid=RSSGUID(content=article.id, is_permalink=False),
        link=str(url),
        title=article.title,
        description=article.description,
        image=str(article.image_url),
        author=article.author,
        pub_date=article.publish_date,
        source=None,
    )

    if source_details:
        item.source = RSSSource(
            name=source_details[article.profile]["name"],
            url=source_details[article.profile]["url"],
        )

    return item


def generate_rss_feed(articles: Sequence[FullArticle], original_url: bool) -> RSSFeed:
    feed: RSSFeed = RSSFeed(
        title="OSINTer",
        link="https://osinter.dk",
        description="OSINTer is in short a framework, or online platform, which aims to automate the heavy-lifting for CTI specialists. In other words, it's a set of open-source tools which can help the trend researchers within cybersecurity spot new trends within the current cyberspace - with a special focus on current threats - and thereby help companies, organisation or individuals tackle the cyberattacks of tomorrow.OSINTer is in short a framework, or online platform, which aims to automate the heavy-lifting for CTI specialists. In other words, it's a set of open-source tools which can help the trend researchers within cybersecurity spot new trends within the current cyberspace - with a special focus on current threats - and thereby help companies, organisation or individuals tackle the cyberattacks of tomorrow.",
        image_url="https://gitlab.com/osinter/osinter/-/raw/master/logo/full.png",
        language="en-us",
        pub_date=datetime.now().astimezone(),
        copyright="© 2023 OSINTer, All rights reserved.",
        managing_editor="skrivtilbertram@gmail.com (Bertram Madsen)",
        webmaster="skrivtilbertram@gmail.com (Bertram Madsen)",
        last_build_date=datetime.now().astimezone(),
        items=[],
    )

    source_details: dict[str, ProfileDetails] = collect_profile_details()

    for article in articles:
        feed.items.append(generate_rss_item(article, original_url, source_details))

    return feed
