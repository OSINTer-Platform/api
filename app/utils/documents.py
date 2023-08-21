from io import BytesIO, StringIO
from typing import cast
from zipfile import ZipFile
from pathvalidate import sanitize_filename

from fastapi import Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from modules.elastic import ArticleSearchQuery
from modules.files import convert_article_to_md
from modules.objects import FullArticle

from .. import config_options
from ..common import EsIDList
from ..dependencies import FastapiArticleSearchQuery


def send_file(
    file_name: str, file_content: StringIO | BytesIO, file_type: str
) -> StreamingResponse:
    response = StreamingResponse(iter([file_content.getvalue()]), media_type=file_type)

    response.headers[
        "Content-Disposition"
    ] = f"attachment; filename={file_name.encode('ascii',errors='ignore').decode()}"

    return response


def convert_ids_to_zip(ids: EsIDList = Query(...)) -> BytesIO:
    return convert_query_to_zip(ArticleSearchQuery(ids=ids))


def convert_query_to_zip(
    search_q: ArticleSearchQuery = Depends(FastapiArticleSearchQuery),
) -> BytesIO:
    search_q.complete = True

    articles: list[FullArticle] = cast(
        list[FullArticle], config_options.es_article_client.query_documents(search_q)
    )

    if articles:
        zip_file = BytesIO()

        with ZipFile(zip_file, "w") as zip_archive:
            for article in articles:
                zip_archive.writestr(
                    f"OSINTer-MD-articles/{sanitize_filename(article.source)}/{sanitize_filename(article.title)}.md",
                    convert_article_to_md(article).getvalue(),
                )

        return zip_file
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Articles not found"
        )
