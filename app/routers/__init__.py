from typing import Literal, TypedDict
from fastapi import APIRouter

from app import config_options
from app.authorization import Area, Level, WebhookLimits, levels_access, webhook_limits

router = APIRouter()


class MLStats(TypedDict):
    cluster: bool
    map: bool
    elser: bool
    assistant: bool


class AuthStats(TypedDict):
    allowed_areas: dict[Level, list[Area]]
    webhook_limits: dict[Literal[Level, "premium"], WebhookLimits]


class Stats(TypedDict):
    ml_availability: MLStats
    auth: AuthStats


@router.get("/app-stats")
def get_applications_stats() -> Stats:
    return {
        "ml_availability": {
            "cluster": config_options.ML_CLUSTERING_AVAILABLE,
            "map": config_options.ML_MAP_AVAILABLE,
            "elser": config_options.ELSER_AVAILABLE,
            "assistant": config_options.LIVE_INFERENCE_AVAILABLE,
        },
        "auth": {"allowed_areas": levels_access, "webhook_limits": webhook_limits},
    }
