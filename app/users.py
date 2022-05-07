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

    class Config:
        arbitrary_types_allowed = True

    def user_exist(self):
        return int(self.es_conn.search(index=self.index_name, body={'query': { "term" : {"username": {"value" : self.username}}}})["hits"]["total"]["value"]) != 0

    def _get_current_user_object(self):
        return self.es_conn.search(index=self.index_name, body={"query" : { "term" : { "username" : { "value" : self.username}}}})["hits"]["hits"][0]

    def _update_current_user(self, field_name, field_value):
        print("\n\n", field_name, field_value, "\n\n")
        if self.user_exist():
            return self.es_conn.update(index=self.index_name, id=self._get_current_user_object()["_id"], doc={field_name : field_value})

    def _get_password_hash(self):
        if self.user_exist():
            return self._get_current_user_object()["_source"]["password_hash"]

    def _set_password_hash(self, passwordHash):
        self._update_current_user(self, "password_hash", passwordHash)

    def change_password(self, password):
        if self.checkIfUserExists():
            self.setPasswordHash(ph.hash(password))

    # Will verify that clear text [password] matches the one for the current user
    def verify_password(self, password):
        if not self.user_exist():
            return False
        else:
            user_hash = self._get_password_hash()

            try:
                ph.verify(user_hash, password)

                if ph.check_needs_rehash(user_hash):
                    self._set_password_hash(ph.hash(password))

                return True

            except argon2.exceptions.VerifyMismatchError:
                return False

class User(BaseUser):
    read_article_ids: List[str] = []
    feeds: Dict[str, Dict[str, Union[str, int, bool, datetime]]] = {}

def create_user(current_user : BaseUser, password : str):

    if current_user.user_exist():
        return False
    else:
        current_user : Dict[ Union[str, List] ] = current_user.dict()

        es_conn = current_user.pop("es_conn")
        index_name = current_user.pop("index_name")

        current_user["password_hash"] = ph.hash(password)

        es_conn.index(index = index_name, document = current_user)

        return True
