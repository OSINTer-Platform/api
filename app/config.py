import os
import secrets

from couchdb import Server

from modules.config import BaseConfig
from modules.elastic import ElasticDB, MLArticleSearchQuery
from modules.objects import FullArticle, MLArticle


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
        self.SECRET_KEY = os.environ.get("SECRET_KEY") or load_secret_key()

        self.ACCESS_TOKEN_EXPIRE_HOURS = int(
            os.environ.get("ACCESS_TOKEN_EXPIRE_HOURS") or 24
        )

        self.REMEMBER_ACCESS_TOKEN_EXPIRE_HOURS = int(
            os.environ.get("REMEMBER_ACCESS_TOKEN_EXPIRE_HOURS") or 24 * 30
        )

        self.JWT_ALGORITHMS = (os.environ.get("JWT_ALGORITHMS") or "HS256").split(" ")

        self.ENABLE_HTTPS = bool(os.environ.get("ENABLE_HTTPS")) or False
        self.ML_CLUSTERING_AVAILABLE = (
            bool(os.environ.get("ML_CLUSTERING_AVAILABLE")) or False
        )
        self.EMAIL_SERVER_AVAILABLE = (
            bool(os.environ.get("EMAIL_SERVER_AVAILABLE")) or False
        )

        self.COUCHDB_URL, self.COUCHDB_NAME = self.get_couchdb_details()
        self.couch_conn = Server(self.COUCHDB_URL)[self.COUCHDB_NAME]

        self.ARTICLE_RENDER_URL = (
            os.environ.get("ARTICLE_RENDER_URL") or "https://osinter.dk/article"
        )

        self.es_ml_article_conn = ElasticDB[
            MLArticle, FullArticle, MLArticleSearchQuery
        ](
            es_conn=self.es_conn,
            index_name=self.ELASTICSEARCH_ARTICLE_INDEX,
            unique_field="url",
            document_object_classes={
                "base": MLArticle,
                "full": FullArticle,
                "search_query": MLArticleSearchQuery,
            },
        )

    @staticmethod
    def get_couchdb_details() -> tuple[str, str]:
        """
        Returns tuble[COUCHDB_URL, COUCHDB_NAME]
        """
        COUCHDB_URL = (
            os.environ.get("COUCHDB_URL") or "http://admin:admin@localhost:5984/"
        )

        COUCHDB_NAME = os.environ.get("USER_DB_NAME") or "osinter_users"

        return COUCHDB_URL, COUCHDB_NAME
