from enum import Enum
from typing import Annotated, Set, TypeAlias
import annotated_types

from pydantic import BaseModel


EsID: TypeAlias = Annotated[str, annotated_types.Len(20, 20)]
EsIDList: TypeAlias = Set[EsID]


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
