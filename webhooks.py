import asyncio
import logging
from collections.abc import Coroutine
from typing import Any
from uuid import UUID
from couchdb.client import ViewResults
from concurrent.futures import ThreadPoolExecutor

from app import config_options
from app.users import models, schemas
from app.dependencies import FastapiArticleSearchQuery
from app.connectors import connectors, webhook_types

from modules.objects import BaseArticle

logger = logging.getLogger("osinter")


def get_articles(
    feeds: list[schemas.Feed],
) -> list[tuple[schemas.Feed, list[BaseArticle]]]:
    def query(feed: schemas.Feed) -> tuple[schemas.Feed, list[BaseArticle]] | None:
        q = FastapiArticleSearchQuery.from_item(feed, [])
        q.limit = min(q.limit, 50)
        articles = config_options.es_article_client.query_documents(q, False)[0]
        articles.reverse()

        existing_article_index: None | int = None

        if feed.webhooks.last_article:
            for i, article in enumerate(articles):
                if article.id == feed.webhooks.last_article:
                    existing_article_index = i

        if existing_article_index is not None:
            articles = articles[existing_article_index + 1 :]
            logger.debug(f"Found {len(articles)} articles for feed with ID {feed.id}")
        else:
            logger.warning(f"Missing last article for feed with ID {feed.id}")

        return (feed, articles) if len(articles) > 0 else None

    with ThreadPoolExecutor(max_workers=20) as executor:
        return [bundle for bundle in executor.map(query, feeds) if bundle]


# Used to handle feeds which have potentially been updated in the meantime
def update_feeds(
    existing_feeds: list[tuple[schemas.Feed, str]], depth: int = 1
) -> None:
    logger.debug(f"Trying to update {len(existing_feeds)} feeds. Attempt nr. {depth}")
    new_feeds_view: ViewResults = models.Feed.all(config_options.couch_conn)
    new_feeds_view.options["keys"] = [str(feed.id) for (feed, _) in existing_feeds]
    new_feeds = [schemas.Feed.model_validate(feed) for feed in new_feeds_view]
    new_feeds_lookup = {feed.id: feed for feed in new_feeds}

    feeds_to_update: list[dict[str, Any]] = []

    for feed, last_article in existing_feeds:
        if not feed.id in new_feeds_lookup:
            logger.error(f"Missing feed with ID {feed.id} during feed update")
            continue

        new_feed = new_feeds_lookup[feed.id]

        # If last_article has been updated, then such has the content of the feed
        # and last_article shouldn't be updated
        if new_feed.webhooks.last_article == feed.webhooks.last_article:
            new_feed.webhooks.last_article = last_article
            feeds_to_update.append(new_feed.db_serialize())
        else:
            logger.warning(
                f"Feed with ID {feed.id} has changed latest article id from {feed.webhooks.last_article} to {new_feed.webhooks.last_article}"
            )

    logger.debug(f"Found {len(feeds_to_update)} feeds available for updating. Updating")
    update_response = config_options.couch_conn.update(feeds_to_update)

    failed_ids: list[str] = [id for (success, id, _) in update_response if not success]
    failed_feeds: list[tuple[schemas.Feed, str]] = []
    existing_feed_lookup = {
        feed.id: (feed, article_id) for (feed, article_id) in existing_feeds
    }

    for id in failed_ids:
        try:
            uuid = UUID(id)
        except ValueError:
            logger.error(f'Recieved failed ID which wasn\'t valid UUID: "{id}"')
            continue

        if uuid in existing_feed_lookup:
            failed_feeds.append(existing_feed_lookup[uuid])
        else:
            logger.error(
                f"Recieved failed ID which wasn't present amongst existing feeds"
            )

    if len(failed_feeds) == 0:
        logger.debug(f"Successfully updated all {len(feeds_to_update)} new feeds")
        return
    elif depth < 3:
        logger.warning(f"Failed to update {len(failed_feeds)} feeds. Retrying")
        update_feeds(failed_feeds, depth + 1)
    else:
        logger.error(
            f"Failed to update {len(failed_feeds)} feeds with the following ids: {[str(feed.id) for (feed, _) in failed_feeds]}"
        )


async def main() -> None:
    ### Query webhooks and feeds ###
    logger.debug("Querying webhooks")
    webhooks = [
        schemas.Webhook.model_validate(webhook)
        for webhook in models.Webhook.all(config_options.couch_conn)
    ]
    feeds_ids = {id for webhook in webhooks for id in webhook.attached_feeds}

    logger.debug(
        f"Found {len(webhooks)} webhooks. Querying related feeds. Expecting {len(feeds_ids)}"
    )
    feeds_view: ViewResults = models.Feed.all(config_options.couch_conn)
    feeds_view.options["keys"] = [str(id) for id in feeds_ids]
    feeds = [schemas.Feed.model_validate(feed) for feed in feeds_view]
    found_ids = [feed.id for feed in feeds]

    if len(feeds_ids) != len(feeds):
        missing_ids = [str(id) for id in feeds_ids if id not in found_ids]
        logger.debug(
            f"Found {len(feeds)} but expected {len(feeds_ids)}. Missing following IDs: '{"' '".join(missing_ids)}'"
        )
    else:
        logger.debug(f"Found {len(feeds)} feeds as expected")

    ### Combine feeds and webhooks ###
    webhook_by_feed: dict[UUID, list[schemas.Webhook]] = {}

    # Combine and validate existence of feed and webhook type
    for webhook in webhooks:
        if webhook.hook_type not in webhook_types:
            logger.error(f"Got unsupported webhook of type {webhook.hook_type}. ID: '{webhook.id}'")
            continue

        for feed_id in webhook.attached_feeds:
            if not feed_id in found_ids:
                continue
            if feed_id not in webhook_by_feed:
                webhook_by_feed[feed_id] = []

            webhook_by_feed[feed_id].append(webhook)

    ### Query articles for feeds ###
    logger.debug("Querying articles for feeds")
    feed_with_articles = get_articles(feeds)

    if len(feed_with_articles) < 1:
        logger.debug("No feeds with new articles found")
        return
    else:
        logger.debug(f"Found {len(feed_with_articles)} feeds with new articles")

    ### Generating webhook tasks ###
    webhook_tasks: list[Coroutine[None, None, None]] = []

    logger.debug("Generating webhook actions")
    for feed, articles in feed_with_articles:
        feed_webhooks: list[schemas.Webhook] = webhook_by_feed[feed.id]

        for webhook in feed_webhooks:
            connector = connectors[webhook.hook_type]
            messages = connector["format"](articles, feed.name)
            webhook_tasks.append(
                connector["send_messages"](
                    [webhook.url.get_secret_value()],
                    messages,  # type: ignore[arg-type]
                )
            )

    logger.debug("Running webhook actions")
    await asyncio.gather(*webhook_tasks, return_exceptions=True)

    update_feeds([(feed, articles[-1].id) for feed, articles in feed_with_articles])


if __name__ == "__main__":
    asyncio.run(main())
