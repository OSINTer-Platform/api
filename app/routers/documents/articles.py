from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import StreamingResponse

from ... import config_options

from modules.elastic import searchQuery
from modules.files import convertArticleToMD
from modules.objects import FullArticle, BaseArticle
from modules.profiles import collectWebsiteDetails

from ...dependencies import fastapiSearchQuery
from ...common import HTTPError

from pydantic import conlist, constr
from typing import List, Dict

from zipfile import ZipFile
from io import BytesIO
from datetime import date

router = APIRouter()


def send_file(file_name, file_content, file_type):
    response = StreamingResponse(iter([file_content.getvalue()]), media_type=file_type)

    response.headers["Content-Disposition"] = f"attachment; filename={file_name}"

    return response


@router.get("/overview/newest", response_model=List[BaseArticle])
async def get_newest_articles():
    return config_options.esArticleClient.queryDocuments(
        searchQuery(limit=50, complete=False)
    )["documents"]


@router.get("/overview/search", response_model=List[FullArticle], response_model_exclude_unset=True)
async def search_articles(query: fastapiSearchQuery = Depends(fastapiSearchQuery)):
    articles = config_options.esArticleClient.queryDocuments(query)["documents"]
    return articles


@router.get("/content", response_model=List[FullArticle])
async def get_article_content(
    IDs: conlist(constr(strip_whitespace=True, min_length=20, max_length=20)) = Query(
        ...
    )
):
    for ID in IDs:
        config_options.esArticleClient.incrementReadCounter(ID)

    return config_options.esArticleClient.queryDocuments(
        searchQuery(IDs=IDs, complete=True)
    )["documents"]


@router.get("/categories", response_model=Dict[str, Dict[str, str]])
async def get_list_of_categories():
    return collectWebsiteDetails(config_options.esArticleClient)


@router.get(
    "/MD/single",
    tags=["download"],
    responses={
        404: {
            "model": HTTPError,
            "description": "Returned requested article doesn't exist",
        }
    },
)
def download_single_markdown_file(
    ID: constr(strip_whitespace=True, min_length=20, max_length=20) = Query(...)
):
    article = config_options.esArticleClient.queryDocuments(
        searchQuery(limit=1, IDs=[ID], complete=True)
    )["documents"][0]

    if article != []:
        articleFile = convertArticleToMD(article)

        return send_file(
            file_name=f"{article.title.replace(' ', '-')}.md",
            file_content=articleFile,
            file_type="text/markdown",
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Article not found"
        )


@router.get(
    "/MD/multiple",
    tags=["download"],
    responses={
        404: {
            "model": HTTPError,
            "description": "Returned when no of the requested article exist",
        }
    },
)
def download_multiple_markdown_files(
    IDs: conlist(constr(strip_whitespace=True, min_length=20, max_length=20)) = Query(
        ...
    )
):
    articles = config_options.esArticleClient.queryDocuments(
        searchQuery(limit=10_000, IDs=IDs, complete=True)
    )["documents"]

    if articles:
        zip_file = BytesIO()

        with ZipFile(zip_file, "w") as zip_archive:
            for article in articles:
                zip_archive.writestr(
                    f"OSINTer-MD-articles/{article.source.replace(' ', '-')}/{article.title.replace(' ', '-')}.md",
                    convertArticleToMD(article).getvalue(),
                )

        return send_file(
            file_name=f"OSINTer-MD-articles-{date.today()}.zip",
            file_content=zip_file,
            file_type="application/zip",
        )

    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Articles not found"
        )
