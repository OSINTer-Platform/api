from enum import Enum

from pydantic import BaseModel, ConstrainedList, ConstrainedStr


class EsID(ConstrainedStr):
    strip_whitespace = True
    min_length = 20
    max_length = 20


class EsIDList(ConstrainedList):
    item_type = EsID
    unique_items = True


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
        schema_extra = {
            "example": {"detail": "HTTPException raised."},
        }
