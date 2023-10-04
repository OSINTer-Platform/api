from typing import Literal

from fastapi import APIRouter

from app import config_options
from .articles import router as article_router

router = APIRouter()


def mount_routers() -> None:
    if config_options.ML_CLUSTERING_AVAILABLE:
        router.include_router(article_router, prefix="/articles", tags=["articles"])


@router.get("/")
def check_ml_availability() -> dict[Literal["clustering"] | Literal["elser"], bool]:
    return {
        "clustering": config_options.ML_CLUSTERING_AVAILABLE,
        "elser": bool(config_options.ELASTICSEARCH_ELSER_PIPELINE),
    }
