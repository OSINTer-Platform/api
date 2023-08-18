from fastapi import APIRouter
from fastapi_rss import RSSResponse

from ....utils.rss import generate_rss_response
from .utils import get_newest_articles

router = APIRouter()


@router.get("/newest/rss")
def get_newest_rss() -> RSSResponse:
    return generate_rss_response(get_newest_articles())
