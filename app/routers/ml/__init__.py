from typing import Literal

from fastapi import APIRouter

from app import config_options
from .articles import router as article_router
from .inference import router as inference_router

router = APIRouter()


def mount_routers() -> None:
    if config_options.ML_CLUSTERING_AVAILABLE:
        router.include_router(article_router, prefix="/articles", tags=["articles"])

    if config_options.LIVE_INFERENCE_AVAILABLE:
        router.include_router(inference_router, prefix="/inference", tags=["inference"])


@router.get("/")
def check_ml_availability() -> (
    dict[Literal["clustering", "elser", "live-inference"], bool]
):
    return {
        "clustering": config_options.ML_CLUSTERING_AVAILABLE,
        "elser": config_options.ELSER_AVAILABLE,
        "live-inference": config_options.LIVE_INFERENCE_AVAILABLE,
    }
