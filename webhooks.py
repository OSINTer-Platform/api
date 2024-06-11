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
) -> list[tuple[schemas.Feed, list[BaseArticle]] | None]:
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
            articles = articles[existing_article_index + 1:]
            logger.debug(f"Found {len(articles)} articles for feed with ID {feed.id}")
        else:
            logger.warning(f"Missing last article for feed with ID {feed.id}")


        return (feed, articles) if len(articles) > 0 else None

    with ThreadPoolExecutor(max_workers=20) as executor:
        return list(executor.map(query, feeds))


# Used to handle feeds which have potentially been updated in the meantime
def update_feeds(existing_feeds: list[tuple[schemas.Feed, str]], depth: int = 1) -> None:
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
            logger.warning(f"Feed with ID {feed.id} has changed latest article id from {feed.webhooks.last_article} to {new_feed.webhooks.last_article}")

    logger.debug(f"Found {len(feeds_to_update)} feeds available for updating. Updating")
    update_response = config_options.couch_conn.update(feeds_to_update)

    failed_ids: list[str] = [id for (success, id, _) in update_response if not success]
    failed_feeds: list[tuple[schemas.Feed, str]] = []
    existing_feed_lookup = {feed.id: (feed, article_id) for (feed, article_id) in existing_feeds}

    for id in failed_ids:
        try:
            uuid = UUID(id)
        except ValueError:
            logger.error(f'Recieved failed ID which wasn\'t valid UUID: "{id}"')
            continue

        if uuid in existing_feed_lookup:
            failed_feeds.append(existing_feed_lookup[uuid])
        else:
            logger.error(f'Recieved failed ID which wasn\'t present amongst existing feeds')

    if len(failed_feeds) == 0:
        logger.debug(f"Successfully updated all {len(feeds_to_update)} new feeds")
        return
    elif depth < 3:
        logger.warning(f"Failed to update {len(failed_feeds)} feeds. Retrying")
        update_feeds(failed_feeds, depth + 1)
    else:
        logger.error(f"Failed to update {len(failed_feeds)} feeds with the following ids: {[str(feed.id) for (feed, _) in failed_feeds]}")


async def main() -> None:
    logger.debug("Querying feeds with webhooks")
    feed_view: ViewResults = models.Feed.all(config_options.couch_conn)
    feeds = [schemas.Feed.model_validate(feed) for feed in feed_view]
    feeds_with_webhooks = [feed for feed in feeds if len(feed.webhooks.hooks) > 0]
    logger.debug(f"Found {len(feeds_with_webhooks)} relevant feeds")

    logger.debug("Querying webhooks")
    webhook_ids = list(
        {
            str(webhook_id)
            for feed in feeds_with_webhooks
            for webhook_id in feed.webhooks.hooks
        }
    )
    webhook_view: ViewResults = models.Webhook.all(config_options.couch_conn)
    webhook_view.options["keys"] = webhook_ids
    webhooks = [schemas.Webhook.model_validate(webhook) for webhook in webhook_view]
    webhook_lookup = {webhook.id: webhook for webhook in webhooks}
    logger.debug(f"Found {len(webhooks)} relevant webhooks")

    logger.debug("Querying articles for feeds")
    feed_with_articles = list(filter(None, get_articles(feeds_with_webhooks)))

    if len(feed_with_articles) < 1:
        logger.debug("No feeds with new articles found")
        return

    webhook_tasks: list[Coroutine[None, None, None]] = []

    logger.debug("Generating webhook actions")
    for feed, articles in feed_with_articles:
        feed_webhooks: list[schemas.Webhook] = []

        # Validating webhooks
        for id in feed.webhooks.hooks:
            if id in webhook_lookup:
                webhook = webhook_lookup[id]
                if webhook.hook_type in webhook_types:
                    feed_webhooks.append(webhook_lookup[id])
                else:
                    logger.error(
                        f"Getting webhook with ID {webhook.id} of type {webhook.hook_type} which isn't supported"
                    )
            else:
                logger.error(f"Missing webhook for ID {id}")

        for webhook in feed_webhooks:
            connector = connectors[webhook.hook_type]
            messages = connector["format"](articles, feed.name)
            webhook_tasks.append(
                connector["send_messages"](
                    [webhook.url.get_secret_value()],
                    messages, # type: ignore[arg-type]
                )
            )

    logger.debug("Running webhook actions")
    await asyncio.gather(*webhook_tasks, return_exceptions=True)

    update_feeds([(feed, articles[-1].id) for feed, articles in feed_with_articles])

if __name__ == "__main__":
    asyncio.run(main())
