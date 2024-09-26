from datetime import UTC, datetime
from typing import TypeGuard, TypeVar

from .common import (
    Area,
    Level,
    WebhookLimits,
    authorization_exception,
    levels,
    levels_access,
    webhook_limits,
)

from app.users.schemas import User


def is_level(level: str) -> TypeGuard[Level]:
    return level in levels


def calc_allowed_areas(user: User | None) -> list[Area]:
    if not user:
        return []

    allowed_areas = set()

    if user.premium:
        allowed_areas.update(levels_access["premium"])
    if user.enterprise:
        allowed_areas.update(levels_access["enterprise"])

    if is_level(user.payment.subscription.level):
        allowed_areas.update(levels_access[user.payment.subscription.level])

    return list(allowed_areas)


def calc_webhook_limits(user: User) -> WebhookLimits:
    def add_limits(l1: WebhookLimits, l2: WebhookLimits) -> WebhookLimits:
        return {
            "max_count": max(l1["max_count"], l2["max_count"]),
            "max_feeds_per_hook": max(
                l1["max_feeds_per_hook"], l2["max_feeds_per_hook"]
            ),
        }

    limits: WebhookLimits = {"max_count": 0, "max_feeds_per_hook": 0}
    allowed = False

    if user.enterprise:
        limits = add_limits(limits, webhook_limits["enterprise"])
        allowed = True
    if user.premium.status:
        limits = add_limits(limits, webhook_limits["premium"])
        allowed = True
    if is_level(user.payment.subscription.level):
        limits = add_limits(limits, webhook_limits[user.payment.subscription.level])
        allowed = True

    if not allowed:
        raise authorization_exception

    return limits


def calc_source_exclusions(allowed_areas: list[Area]) -> list[str]:
    areas_to_fields: dict[Area, str] = {
        "map": "ml.coordinates",
        "cluster": "ml.cluster",
        "similar": "similar",
        "summary": "summary",
    }

    return [v for k, v in areas_to_fields.items() if not k in allowed_areas]


def authorize_user(user: User, areas: list[Area]) -> bool:
    allowed_areas = calc_allowed_areas(user)

    for area in areas:
        if area not in allowed_areas:
            return False

    return True


UserType = TypeVar("UserType", bound=User)


def expire_premium(user: UserType) -> UserType:
    if (
        user.premium.expire_time > 0
        and user.premium.expire_time < datetime.now(UTC).timestamp()
    ):
        user.premium.status = False
        user.premium.expire_time = 0

    return user
