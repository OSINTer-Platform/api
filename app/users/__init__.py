from couchdb import Server, Database
from couchdb.http import PreconditionFailed
from couchdb.mapping import ViewDefinition

from .. import config_options
from .models import views


from couchdb import Database, Server
from .. import config_options


def get_db_conn() -> Database:
    return Server(config_options.COUCHDB_URL)[config_options.COUCHDB_NAME]


def init_db():
    couch = Server(config_options.COUCHDB_URL)

    try:
        db = couch.create(config_options.COUCHDB_NAME)
    except PreconditionFailed:
        db = couch[config_options.COUCHDB_NAME]

    ViewDefinition.sync_many(db, views)
