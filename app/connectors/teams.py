from typing import Any, Coroutine, TypedDict
import aiohttp
import asyncio
import re

from modules.objects.articles import BaseArticle
from app import config_options


AdaptiveCardContent = TypedDict(
    "AdaptiveCardContent",
    {
        "type": str,
        "body": list[dict[str, Any]],
        "selectAction": dict[str, str],
        "$schema": str,
        "version": str,
    },
)


class AdaptiveCard(TypedDict):
    contentType: str
    content: AdaptiveCardContent


url_pattern = re.compile(r"https://prod-[0-9]+\.\w+\.logic\.azure\.com:443/workflows.*")


def format(articles: list[BaseArticle], feed_name: str) -> list[AdaptiveCard]:
    def generate_body(article: BaseArticle) -> list[dict[str, Any]]:
        return [
            {
                "type": "TextBlock",
                "text": article.title,
                "weight": "Bolder",
                "size": "Large",
                "wrap": True,
            },
            {
                "type": "TextBlock",
                "text": article.description,
                "wrap": True,
            },
            {
                "type": "Image",
                "url": article.image_url,
            },
            {
                "type": "ColumnSet",
                "columns": [
                    {
                        "type": "Column",
                        "width": "stretch",
                        "items": [
                            {
                                "type": "TextBlock",
                                "text": f'From "{feed_name}"',
                                "wrap": True,
                                "isSubtle": True,
                                "weight": "Default",
                                "fontType": "Default",
                            }
                        ],
                    },
                    {
                        "type": "Column",
                        "width": "stretch",
                        "items": [
                            {
                                "type": "TextBlock",
                                "text": article.publish_date.strftime("%m/%d/%Y %H:%M"),
                                "wrap": True,
                                "horizontalAlignment": "Right",
                                "isSubtle": True,
                            }
                        ],
                    },
                ],
            },
        ]

    return [
        {
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": {
                "type": "AdaptiveCard",
                "body": generate_body(article),
                "selectAction": {
                    "type": "Action.OpenUrl",
                    "title": "Open Article",
                    "url": f"{config_options.ARTICLE_RENDER_URL}/{article.id}",
                },
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "version": "1.3",
            },
        }
        for article in articles
    ]


async def send_messages(urls: list[str], messages: list[AdaptiveCard]) -> None:
    send_actions: list[Coroutine[Any, Any, None]] = []

    async def send(
        url: str,
        messages: list[AdaptiveCard],
        session: aiohttp.ClientSession,
        attempt: int = 1,
        max_attempts: int = 3,
    ) -> None:
        if attempt > max_attempts:
            return

        message = {"type": "message", "attachments": messages}
        async with session.post(url, json=message) as response:
            if not response.ok:
                await send(url, messages, session, attempt + 1)

    async with aiohttp.ClientSession() as session:
        for url in urls:
            send_actions.append(send(url, messages, session))

        await asyncio.gather(*send_actions, return_exceptions=True)


async def validate(url: str) -> bool:
    if not url_pattern.fullmatch(url):
        return False

    init_message = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "type": "AdaptiveCard",
                    "body": [
                        {
                            "type": "TextBlock",
                            "text": "Initializing webhook from OSINTer...",
                            "weight": "Bolder",
                            "size": "Large",
                            "wrap": True,
                        },
                    ],
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "version": "1.3",
                },
            }
        ],
    }

    async with aiohttp.ClientSession() as session:
        for _ in range(3):
            r = await session.post(url, json=init_message)
            if r.ok:
                return True

    return False
