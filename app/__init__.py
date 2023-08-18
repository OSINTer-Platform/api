from dotenv import load_dotenv

from modules.config import configure_logger
from modules.misc import create_folder

from .config import FrontendConfig

from couchdb import Server
from couchdb.http import PreconditionFailed


def init_db(url: str, db_name: str) -> None:
    couch = Server(url)

    try:
        couch.create(db_name)
    except PreconditionFailed:
        pass

    return None


load_dotenv()

create_folder("logs")
configure_logger("osinter")


init_db(*FrontendConfig.get_couchdb_details())

config_options = FrontendConfig()
