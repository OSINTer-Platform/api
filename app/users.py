import argon2
import secrets

from elasticsearch import Elasticsearch
from pydantic import BaseModel
from typing import List, Dict, Union

ph = argon2.PasswordHasher()

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

    def _get_password_hash(self):
        if self.user_exist():
            return self._get_current_user_object()["_source"]["password_hash"]

    def _set_password_hash(self, passwordHash):
        if self.user_exist():
            return self.es_conn.update(index=self.index_name, id=self._get_current_user_object()["_id"], doc={"password_hash" : passwordHash})

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
