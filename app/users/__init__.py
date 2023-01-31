from couchdb import Database, Server
from couchdb.client import Server
from couchdb.http import PreconditionFailed

from .. import config_options


def get_db_conn() -> Database:
    return Server(config_options.COUCHDB_URL)[config_options.COUCHDB_NAME]


couch = Server(config_options.COUCHDB_URL)

try:
    db = couch.create(config_options.COUCHDB_NAME)
except PreconditionFailed:
    db = couch[config_options.COUCHDB_NAME]
