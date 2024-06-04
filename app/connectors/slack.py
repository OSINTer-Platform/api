import re
from typing import Any, Coroutine, TypeAlias
import asyncio

from slack_sdk.webhook.async_client import AsyncWebhookClient
from slack_sdk.http_retry.builtin_async_handlers import AsyncRateLimitErrorRetryHandler

from modules.objects import BaseArticle
from app import config_options

BlockMsg: TypeAlias = dict[str, Any]

url_pattern = re.compile(
    r"https://hooks\.slack\.com/services/T[a-zA-Z0-9]+/B[a-zA-Z0-9]+/[a-zA-Z0-9]+"
)


def format(articles: list[BaseArticle], feed_name: str) -> list[list[BlockMsg]]:
    def create_blocks(article: BaseArticle) -> list[BlockMsg]:
        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": article.title,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "plain_text",
                    "text": article.description,
                },
            },
            {
                "type": "image",
                "image_url": article.image_url,
                "alt_text": "Article Image",
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "style": "primary",
                        "text": {
                            "type": "plain_text",
                            "text": "Go to article",
                        },
                        "value": "article-link",
                        "url": f"{config_options.ARTICLE_RENDER_URL}/{article.id}",
                    }
                ],
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "plain_text",
                        "text": f'From "{feed_name}" | {article.publish_date.strftime("%m/%d/%Y %H:%M")}',
                    }
                ],
            },
        ]

    return [create_blocks(article) for article in articles]


async def send_messages(messages: list[tuple[list[str], list[list[BlockMsg]]]]) -> None:
    send_actions: list[Coroutine[Any, Any, None]] = []
    rate_limit_handler = AsyncRateLimitErrorRetryHandler(max_retry_count=10)

    async def send(url: str, blocks: list[BlockMsg]) -> None:
        webhook = AsyncWebhookClient(url)
        webhook.retry_handlers.append(rate_limit_handler)

        r = await webhook.send(blocks=blocks)

        if r.status_code == 400 and "invalid_blocks" in r.body:
            for block in blocks:
                if "type" in block and block["type"] == "image":
                    block["image_url"] = config_options.FULL_LOGO_URL

            for _ in range(3):
                r = await webhook.send(blocks=blocks)
                if r.status_code != 400:
                    break

    for urls, block_batches in messages:
        for url in urls:
            for blocks in block_batches:
                send_actions.append(send(url, blocks))

    await asyncio.gather(*send_actions, return_exceptions=True)


async def validate(url: str) -> bool:
    if url_pattern.search(url) is None:
        return False

    webhook = AsyncWebhookClient(url)

    r = await webhook.send(text="Initializing webhook from OSINTer...")

    for _ in range(3):
        if r.status_code == 200:
            break
        r = await webhook.send(text="Initializing webhook from OSINTer...")

    if r.status_code == 200:
        return True
    else:
        return False
