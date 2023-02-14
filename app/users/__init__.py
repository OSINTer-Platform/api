from couchdb import Server
from couchdb.client import Server
from couchdb.http import PreconditionFailed
from couchdb.mapping import ViewDefinition

from .. import config_options
from .models import views


couch = Server(config_options.COUCHDB_URL)

try:
    db = couch.create(config_options.COUCHDB_NAME)
except PreconditionFailed:
    db = couch[config_options.COUCHDB_NAME]

ViewDefinition.sync_many(db, views)

from .standard import create_items

create_items()
