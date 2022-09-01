from fastapi import APIRouter

from .. import config_options

router = APIRouter()


@router.get("/")
def check_ml_availability():
    return {"available": config_options.ML_AVAILABLE}
