from datetime import datetime
from typing import Annotated, Iterable, cast
from fastapi import APIRouter, Body, Depends, Query

from app import config_options
from app.users import models, schemas
from app.users.auth import ensure_user_from_token


router = APIRouter()


@router.post("/submit")
def submit_survey(
    contents: Annotated[list[schemas.SurveySection], Body()],
    current_user: Annotated[schemas.User, Depends(ensure_user_from_token)],
    version: Annotated[int, Body()],
) -> None:
    survey = schemas.Survey(
        contents=contents,
        version=version,
        metadata=schemas.SurveyMetaData(
            user_id=current_user.id, submission_date=datetime.now()
        ),
    )

    config_options.couch_conn[str(survey.id)] = survey.db_serialize(exclude={"id"})


@router.get("/", response_model=list[schemas.Survey])
def get_submittet_surveys(
    version: Annotated[int, Query()],
    current_user: Annotated[schemas.User, Depends(ensure_user_from_token)],
) -> list[models.Survey]:
    user_surveys = cast(
        Iterable[models.Survey],
        models.Survey.by_user_id(config_options.couch_conn)[str(current_user.id)],
    )

    return [survey for survey in user_surveys if survey.version == version]
