from . import config_options
from .utils import get_newest_articles

from fastapi import APIRouter

from fastapi_rss import RSSResponse

from modules.elastic import SearchQuery
from modules.objects import BaseArticle

from ....utils.rss import generate_rss_response

router = APIRouter()

@router.get("/newest/rss")
def get_newest_rss() -> RSSResponse:
    return generate_rss_response(get_newest_articles())
