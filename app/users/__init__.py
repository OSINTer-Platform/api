from .models import views
from couchdb import Database, Server
from .. import config_options


def init_db():
    couch = Server(config_options.COUCHDB_URL)

    try:
        db = couch.create(config_options.COUCHDB_NAME)
    except PreconditionFailed:
        db = couch[config_options.COUCHDB_NAME]

    ViewDefinition.sync_many(db, views)
