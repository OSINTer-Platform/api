# Standard config section
import multiprocessing

max_requests = 1000
max_requests_jitter = 50

log_file = "-"

workers = multiprocessing.cpu_count() * 2 + 1

# App specific
from app import config_options
from app.config import FrontendConfig

from app.users.models import views
from app.users.standard import create_standard_items

from couchdb.mapping import ViewDefinition


def on_starting(_):
    ViewDefinition.sync_many(config_options.couch_conn, views)
    create_standard_items()


def post_fork(_, __):
    global config_options
    config_options = FrontendConfig()


if __name__ == "__main__":
    on_starting(None)
