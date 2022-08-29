from fastapi import Query, HTTPException, status, Depends
from fastapi.responses import StreamingResponse

from .. import config_options

from modules.elastic import SearchQuery
from modules.files import convert_article_to_md

from ..dependencies import FastapiSearchQuery

from pydantic import conlist, constr

from zipfile import ZipFile
from io import BytesIO


def send_file(file_name: str, file_content: BytesIO, file_type: str):
    response = StreamingResponse(iter([file_content.getvalue()]), media_type=file_type)

    response.headers[
        "Content-Disposition"
    ] = f"attachment; filename={file_name.encode('ascii',errors='ignore').decode()}"

    return response


async def convert_ids_to_zip(
    ids: conlist(
        constr(strip_whitespace=True, min_length=20, max_length=20), unique_items=True
    ) = Query(...)
):
    return await convert_query_to_zip(SearchQuery(ids=ids))


async def convert_query_to_zip(
    search_q: FastapiSearchQuery = Depends(FastapiSearchQuery),
):

    search_q.complete = True

    articles = config_options.es_article_client.query_documents(search_q)["documents"]

    if articles:
        zip_file = BytesIO()

        with ZipFile(zip_file, "w") as zip_archive:
            for article in articles:
                zip_archive.writestr(
                    f"OSINTer-MD-articles/{article.source.replace(' ', '-')}/{article.title.replace(' ', '-')}.md",
                    convert_article_to_md(article).getvalue(),
                )

        return zip_file
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Articles not found"
        )
