from io import BytesIO, StringIO
from zipfile import ZipFile
from pathvalidate import sanitize_filename

from fastapi import Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from modules.files import article_to_md
from modules.objects.articles import FullArticle

from .. import config_options
from ..dependencies import (
    FastapiArticleSearchQuery,
    FastapiQueryParamsArticleSearchQuery,
)

# TODO:Optimize functions sending files (especially the zip file) as to not save
# files in memory but on disk


def send_file(
    file_name: str, file_content: str | StringIO | BytesIO, file_type: str
) -> StreamingResponse:
    if isinstance(file_content, str):
        response = StreamingResponse(iter([file_content]), media_type=file_type)
    else:
        response = StreamingResponse(
            iter([file_content.getvalue()]), media_type=file_type
        )

    response.headers["Content-Disposition"] = (
        f"attachment; filename={file_name.encode('ascii',errors='ignore').decode()}"
    )

    return response


def convert_article_query_to_zip(
    search_q: FastapiArticleSearchQuery = Depends(FastapiQueryParamsArticleSearchQuery),
) -> BytesIO:
    articles = config_options.es_article_client.query_documents(search_q, True)[0]

    if articles:
        return convert_articles_to_zip(articles)
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Articles not found"
        )


def convert_articles_to_zip(articles: list[FullArticle]) -> BytesIO:
    zip_file = BytesIO()

    with ZipFile(zip_file, "w") as zip_archive:
        for article in articles:
            zip_archive.writestr(
                f"OSINTer-MD-articles/{sanitize_filename(article.source)}/{sanitize_filename(article.title)}.md",
                article_to_md(article),
            )

    return zip_file
