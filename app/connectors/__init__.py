import typing
from typing import Callable, Coroutine, Generic, Literal, TypeAlias, TypeVar, TypedDict
from discord import Embed

from modules.objects.articles import BaseArticle
from . import discord, slack, teams


WebhookType: TypeAlias = Literal["discord", "slack", "teams"]
webhook_types = typing.get_args(WebhookType)

ConnectorInput = TypeVar("ConnectorInput")


class Connector(TypedDict, Generic[ConnectorInput]):
    format: Callable[[list[BaseArticle], str], ConnectorInput]
    send_messages: Callable[[list[str], ConnectorInput], Coroutine[None, None, None]]
    validate: Callable[[str], Coroutine[None, None, bool]]


class ConnectorOverview(TypedDict, total=True):
    discord: Connector[list[list[Embed]]]
    slack: Connector[list[list[slack.BlockMsg]]]
    teams: Connector[list[teams.AdaptiveCard]]


connectors: ConnectorOverview = {
    "discord": {
        "format": discord.format,
        "send_messages": discord.send_messages,
        "validate": discord.validate,
    },
    "slack": {
        "format": slack.format,
        "send_messages": slack.send_messages,
        "validate": slack.validate,
    },
    "teams": {
        "format": teams.format,
        "send_messages": teams.send_messages,
        "validate": teams.validate,
    },
}
