from enum import Enum
from typing import Annotated, Literal, Set, TypeAlias
import annotated_types

from pydantic import BaseModel


EsID: TypeAlias = Annotated[str, annotated_types.Len(32, 32)]
EsIDList: TypeAlias = Set[EsID]

ArticleSortBy = Literal[
    "publish_date", "read_times", "source", "author", "inserted_at", ""
]

CVESortBy = Literal["document_count", "cve", "publish_date", "modified_date", ""]

ClusterSortBy = Literal["document_count", "nr", ""]


class DefaultResponseStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class DefaultResponse(BaseModel):
    status: DefaultResponseStatus
    msg: str = ""

    class Config:
        use_enum_values = True


class HTTPError(BaseModel):
    detail: str
    headers: dict[str, str]

    class Config:
        json_schema_extra = {
            "example": {"detail": "HTTPException raised."},
        }
