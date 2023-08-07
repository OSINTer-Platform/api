from app.users import init_db
from app import config_options
from app.config import FrontendConfig

from app.users.standard import create_standard_items


def on_starting(_):
    init_db()
    create_standard_items()

def post_fork(_, __):
    global config_options
    config_options = FrontendConfig()

if __name__ == "__main__":
    on_starting(None)
