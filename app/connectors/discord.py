import asyncio
from typing import Any, Coroutine
from discord import Embed, Webhook
import aiohttp

from modules.objects import BaseArticle
from app import config_options


def format(articles: list[BaseArticle], feed_name: str) -> list[list[Embed]]:
    def create_embed(article: BaseArticle) -> Embed:
        embed = Embed(
            title=article.title,
            url=f"{config_options.ARTICLE_RENDER_URL}/{article.id}",
            description=f"**{article.description}**",
            colour=0xD4163C,
            timestamp=article.publish_date,
        )

        embed.set_image(url=article.image_url)

        embed.set_footer(text=f'From "{feed_name}"')

        return embed

    batches: list[list[Embed]] = [[]]
    batch_length = 0

    for article in articles:
        new_embed = create_embed(article)
        embed_length = len(new_embed)

        if embed_length + batch_length > 6000 or len(batches[-1]) > 9:
            batches.append([])
            batch_length = 0

        batches[-1].append(new_embed)
        batch_length += embed_length

    return batches


async def send_messages(urls: list[str], message_batches: list[list[Embed]]) -> None:
    async with aiohttp.ClientSession() as session:
        send_actions: list[Coroutine[Any, Any, None]] = []

        for url in urls:
            try:
                webhook = Webhook.from_url(url, session=session)
                for messages in message_batches:
                    action = webhook.send(
                        "",
                        wait=False,
                        embeds=messages,
                        username="OSINTer",
                        avatar_url=config_options.SMALL_LOGO_URL,
                    )
                    send_actions.append(action)
            except ValueError:
                pass

        await asyncio.gather(*send_actions, return_exceptions=True)


async def validate(url: str) -> bool:
    try:
        async with aiohttp.ClientSession() as session:
            webhook = Webhook.from_url(url, session=session)
            await webhook.send("Initializing webhook from OSINTer...", silent=True)
        return True
    except:
        return False
