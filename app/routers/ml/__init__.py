from typing import Literal

from fastapi import APIRouter

from app import config_options
from .clusters import router as cluster_router
from .map import router as map_router
from .inference import router as inference_router

router = APIRouter(tags=["ml"])


def mount_routers() -> None:
    if config_options.ML_CLUSTERING_AVAILABLE:
        router.include_router(cluster_router, tags=["cluster"])

    if config_options.ML_MAP_AVAILABLE:
        router.include_router(map_router, tags=["map"])

    if config_options.LIVE_INFERENCE_AVAILABLE:
        router.include_router(inference_router, prefix="/inference", tags=["inference"])


@router.get("/")
def check_ml_availability() -> (
    dict[Literal["cluster", "map", "elser", "assistant"], bool]
):
    return {
        "cluster": config_options.ML_CLUSTERING_AVAILABLE,
        "map": config_options.ML_MAP_AVAILABLE,
        "elser": config_options.ELSER_AVAILABLE,
        "assistant": config_options.LIVE_INFERENCE_AVAILABLE,
    }
