from uuid import UUID
from app.users import schemas
from app.users import crud

from secrets import token_urlsafe

standard_feeds = {
    "Bitcoin": schemas.FeedCreate(
        source_category={
            "arstechnica",
            "bleepingcomputer",
            "computerworld",
            "cso",
            "cyberscoop",
            "cybersecuritydive",
            "cybersecuritynews",
            "darkreading",
            "dfirreport",
            "infosecuritynews",
            "latesthackingnews",
            "nakedsecurity",
            "securityaffairs",
            "securityweek",
            "thehackernews",
            "therecord",
            "threatpost",
            "trendmicro",
            "zdnet",
        },
        search_term="bitcoin",
        highlight=True,
    ),
    "Log4J": schemas.FeedCreate(
        source_category={
            "arstechnica",
            "bleepingcomputer",
            "computerworld",
            "cso",
            "thehackernews",
            "therecord",
            "threatpost",
            "trendmicro",
            "zdnet",
        },
        search_term="log4j",
        highlight=True,
    ),
    "Ransomware": schemas.FeedCreate(
        source_category={
            "cso",
            "cyberscoop",
            "cybersecuritydive",
            "cybersecuritynews",
            "darkreading",
            "dfirreport",
            "infosecuritynews",
            "latesthackingnews",
            "nakedsecurity",
            "securityaffairs",
            "securityweek",
            "thehackernews",
            "therecord",
        },
        search_term="ransomware",
        highlight=True,
    ),
}


def create_standard_items() -> None:
    crud.remove_user("OSINTer")
    crud.create_user(username="OSINTer", password=token_urlsafe(64), id=UUID(int=0))

    stored_feeds: set[UUID] = set()

    for feed_name, feed in standard_feeds.items():
        new_feed = crud.create_feed(feed_params=feed, name=feed_name, owner=UUID(int=0))
        stored_feeds.add(new_feed.id)

    crud.modify_user_subscription(
        user_id=UUID(int=0), ids=stored_feeds, action="subscribe", item_type="feed"
    )
