from datetime import timedelta
import os
import secrets

from couchdb import Server

from modules.config import BaseConfig


from uuid import uuid4
from logging import getLogger

logger = getLogger("osinter")


def load_secret_key() -> str:
    if os.path.isfile("secret.key"):
        with open("secret.key", "r") as key_file:
            return key_file.read()
    else:
        current_secret_key: str = secrets.token_urlsafe(256)
        with os.fdopen(
            os.open("secret.key", os.O_WRONLY | os.O_CREAT, 0o400), "w"
        ) as key_file:
            key_file.write(current_secret_key)
        return current_secret_key


class FrontendConfig(BaseConfig):
    def __init__(self) -> None:
        super().__init__()
        self.STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY", None)
        self.STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", None)

        for needed_secret in ["STRIPE_API_KEY", "STRIPE_WEBHOOK_SECRET"]:
            if not self[needed_secret]:
                logger.warn(f"Missing {needed_secret}. Stripe integration may not function")

        self.SECRET_KEY = os.environ.get("SECRET_KEY") or load_secret_key()

        self.ACCESS_TOKEN_EXPIRE_HOURS = int(
            os.environ.get("ACCESS_TOKEN_EXPIRE_HOURS") or 24
        )

        self.REMEMBER_ACCESS_TOKEN_EXPIRE_HOURS = int(
            os.environ.get("REMEMBER_ACCESS_TOKEN_EXPIRE_HOURS") or 24 * 30
        )

        self.JWT_ALGORITHMS = (os.environ.get("JWT_ALGORITHMS") or "HS256").split(" ")

        self.ENABLE_HTTPS = self.get_env_bool("ENABLE_HTTPS")
        self.ML_CLUSTERING_AVAILABLE = self.get_env_bool("ML_CLUSTERING_AVAILABLE")
        self.ML_MAP_AVAILABLE = self.get_env_bool("ML_MAP_AVAILABLE")
        self.LIVE_INFERENCE_AVAILABLE = self.ELSER_AVAILABLE and bool(self.OPENAI_KEY)

        self.EMAIL_SERVER_AVAILABLE = self.get_env_bool("EMAIL_SERVER_AVAILABLE")

        self.couch_conn = Server(self.COUCHDB_URL)[self.COUCHDB_NAME]

        self.id = uuid4()

        self.ARTICLE_RENDER_URL = (
            os.environ.get("ARTICLE_RENDER_URL") or "https://osinter.dk/article"
        )

        self.FULL_LOGO_URL = os.environ.get("FULL_LOGO_URL") or "https://osinter.dk/fullLogo.png"
        self.SMALL_LOGO_URL = os.environ.get("SMALL_LOGO_URL") or "https://osinter.dk/fullLogo.png"

        signup_code = os.environ.get("SIGNUP_CODES", "")
        self.SIGNUP_CODES: dict[str, timedelta] = {}
        for code_pair in signup_code.split(","):
            if not code_pair:
                continue
            try:
                code, day_diff_str = code_pair.split(":")
                day_diff = int(day_diff_str)
                diff = timedelta(days=day_diff)

                self.SIGNUP_CODES[code] = diff
            except:
                raise Exception(f"Error when parsing following signup code-string: {code_pair}")

    @staticmethod
    def get_env_bool(key: str) -> bool:
        return bool(os.environ.get(key)) or False
