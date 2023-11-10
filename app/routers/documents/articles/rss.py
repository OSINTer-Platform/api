from fastapi import APIRouter, Query, Request, Response
from fastapi.templating import Jinja2Templates

from app import config_options
from app.dependencies import FastapiArticleSearchQuery
from app.utils.rss import generate_rss_feed

router = APIRouter()

jinja_templates = Jinja2Templates(directory="app/templates")


class XMLResponse(Response):
    media_type = "application/xml"


@router.get("/newest/rss")
def get_newest_rss(
    request: Request, original_url: bool = Query(False), limit: int = Query(50)
) -> Response:
    articles = config_options.es_article_client.query_documents(
        FastapiArticleSearchQuery(
            limit=limit, sort_by="publish_date", sort_order="desc", premium=False
        ),
        True,
    )[0]

    return jinja_templates.TemplateResponse(
        "rssv2.j2",
        {"request": request, "feed": generate_rss_feed(articles, original_url)},
        headers={"content-type": "application/xml"},
    )
