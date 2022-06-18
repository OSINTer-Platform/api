import argon2
import secrets

from elasticsearch import Elasticsearch
from pydantic import BaseModel
from typing import List, Dict, Union, Optional

from datetime import datetime

ph = argon2.PasswordHasher()

# This is a datamodel used for storing information about a users feed. A feed for a user, is simply a set of query paramaters, used for search for articles relevant to a user, when that feed is selected.
class Feed(BaseModel):
    feed_name: str
    limit: Optional[int] = None
    sortBy: Optional[str] = None
    sortOrder: Optional[str] = None
    searchTerm: Optional[str] = None
    firstDate: Optional[datetime] = None
    lastDate: Optional[datetime] = None
    sourceCategory: Optional[List[str]] = None
    highlight: Optional[bool] = None


class BaseUser(BaseModel):
    username: str
    index_name: str
    es_conn: Elasticsearch
    user_details: Dict = {}

    class Config:
        arbitrary_types_allowed = True

    def user_exist(self):
        queryResponse = self.es_conn.search(
            index=self.index_name,
            body={"query": {"term": {"username": {"value": self.username}}}},
        )

        if int(queryResponse["hits"]["total"]["value"]) != 0:
            self.user_details = queryResponse["hits"]["hits"][0]
            return True
        else:
            return False

    def _cache_current_user_object(self):
        self.user_details = self.es_conn.search(
            index=self.index_name,
            body={"query": {"term": {"username": {"value": self.username}}}},
        )["hits"]["hits"][0]

        return self.user_details

    def _update_current_user(self, field_name, field_value, overwrite=False):

        if overwrite:
            return self.es_conn.update(
                index=self.index_name,
                id=self.user_details["_id"],
                refresh=True,
                script={
                    "source": f"""
                            ctx._source["{field_name}"].clear();
                            ctx._source["{field_name}"] = params.new_object;
                        """,
                    "params": {"new_object": field_value},
                },
            )

        else:
            return self.es_conn.update(
                index=self.index_name,
                id=self.user_details["_id"],
                refresh=True,
                doc={field_name: field_value},
            )

    def _set_password_hash(self, passwordHash):
        self._update_current_user(self, "password_hash", passwordHash)

    def _set_email_hash(self, email_hash):
        self._update_current_user(self, "email_hash", email_hash)

    def _verify_hashed_value(self, value, hash_value, updateMethod):
        try:
            ph.verify(hash_value, value)

            if ph.check_needs_rehash(hash_value):
                updateMethod(ph.hash(password))

            return True

        except argon2.exceptions.VerifyMismatchError:
            return False

    def change_password(self, password):
        if self.user_exists():
            self.setPasswordHash(ph.hash(password))

    # Will verify that clear text [password] matches the one for the current user
    def verify_password(self, password):
        if self.user_exist():
            return self._verify_hashed_value(
                password,
                self.user_details["_source"]["password_hash"],
                self._set_password_hash,
            )
        else:
            return False

    def verify_email(self, email):
        if self.user_exist():
            return self._verify_hashed_value(
                email,
                self.user_details["_source"]["email_hash"],
                self._set_email_hash,
            )
        else:
            return False


class User(BaseUser):
    read_article_ids: List[str] = []
    feeds: Dict[str, Dict[str, Union[str, int, bool, datetime]]] = {}
    collections: Dict[str, List[str]] = {"Read Later": [], "Already Read": []}

    def _get_feed_list(self):
        return [self.feeds[feed_name].dict() for feed_name in self.feeds]

    def get_collections(self):
        if not self.user_exist():
            return {"Read Later": [], "Already Read": []}

        self.collections = self.user_details["_source"]["collections"]

        return self.collections

    def modify_collections(self, action, collection_name, IDs=None):
        if not self.get_collections():
            return False

        if action == "add":
            if collection_name in self.collections:
                return False
            else:
                self.collections[collection_name] = []

        else:
            if not collection_name in self.collections:
                return False

            if action == "remove":
                self.collections.pop(collection_name)

            elif action == "extend":
                for ID in IDs:
                    if not ID in self.collections[collection_name]:
                        self.collections[collection_name].append(ID)

            elif action == "subtract":
                for ID in IDs:
                    try:
                        self.collections[collection_name].remove(ID)
                    except ValueError:
                        pass

            elif action == "clear":
                self.collections[collection_name] = []

        self._update_current_user("collections", self.collections, overwrite=True)

        return True

    def get_feeds(self):
        if not self.user_exist():
            return []

        self.feeds = {}

        user_data = self.user_details["_source"]

        if "feeds" in user_data:
            for feed in user_data["feeds"]:
                feed_name = feed["feed_name"]
                self.feeds[feed_name] = Feed(**feed)

        return self._get_feed_list()

    # Will ad feed if given feed object or remove feed if only given name
    def update_feed_list(self, feed=None, feed_name=None):
        self.get_feeds()

        if not self.user_exist():
            return False
        else:
            if feed:
                if feed.feed_name in self.feeds:
                    return False

                self.feeds[feed.feed_name] = feed

            elif feed_name:
                try:
                    self.feeds.pop(feed_name)
                except KeyError:
                    return False

            else:
                return False

            self._update_current_user("feeds", self._get_feed_list())

            return True


def create_user(current_user: BaseUser, password: str, email: str = ""):

    if current_user.user_exist():
        return False
    else:
        current_user: Dict[Union[str, List]] = current_user.dict()

        current_user.pop("user_details")
        es_conn = current_user.pop("es_conn")
        index_name = current_user.pop("index_name")

        current_user["password_hash"] = ph.hash(password)

        if email:
            current_user["email_hash"] = ph.hash(email)
        else:
            current_user["email_hash"] = ""

        es_conn.index(index=index_name, document=current_user)

        return True
