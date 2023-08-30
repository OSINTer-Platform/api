from typing_extensions import TypedDict

from modules.profiles import get_profiles

from .. import config_options


class ProfileDetails(TypedDict):
    name: str
    image: str
    url: str


def collect_profile_details() -> dict[str, ProfileDetails]:
    db_stored_profiles = list(
        config_options.es_article_client.get_unique_values(field_name="profile").keys()
    )

    profiles = sorted(
        get_profiles(), key=lambda profile: profile["source"]["profile_name"]
    )

    details: dict[str, ProfileDetails] = {}

    for profile in profiles:
        if (profile_name := profile["source"]["profile_name"]) in db_stored_profiles:
            image_url = profile["source"]["image_url"]

            details[profile_name] = {
                "name": profile["source"]["name"],
                "image": image_url,
                "url": profile["source"]["address"],
            }

    return details
