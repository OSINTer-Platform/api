from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.templating import Jinja2Templates

from app import config_options
from app.users.auth.authorization import UserAuthorizer
from app.dependencies import FastapiArticleSearchQuery, SourceExclusions
from app.utils.rss import generate_rss_feed

ArticleAuthorizer = UserAuthorizer(["articles"])

router = APIRouter(dependencies=[Depends(ArticleAuthorizer)])

jinja_templates = Jinja2Templates(directory="app/templates")


class XMLResponse(Response):
    media_type = "application/xml"


@router.get("/newest/rss")
def get_newest_rss(
    request: Request,
    source_exclusions: SourceExclusions,
    original_url: bool = Query(False),
    limit: int = Query(50),
) -> Response:
    articles = config_options.es_article_client.query_documents(
        FastapiArticleSearchQuery(
            source_exclusions, limit=limit, sort_by="publish_date", sort_order="desc"
        ),
        True,
    )[0]

    return jinja_templates.TemplateResponse(
        "rssv2.j2",
        {"request": request, "feed": generate_rss_feed(articles, original_url)},
        headers={"content-type": "application/xml"},
    )
