from couchdb import Server
from couchdb.http import PreconditionFailed
from couchdb.mapping import ViewDefinition

from dotenv import load_dotenv

from config import FrontendConfig

load_dotenv()

couch = Server(FrontendConfig.get_couchdb_details()[0])

try:
    couch.create(FrontendConfig.get_couchdb_details()[1])
except PreconditionFailed:
    pass


from app import config_options

from app.users.models import views
from app.users.standard import create_standard_items

ViewDefinition.sync_many(config_options.couch_conn, views)
create_standard_items()
