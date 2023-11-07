from dotenv import load_dotenv

from modules.config import configure_logger
from modules.misc import create_folder

from config import FrontendConfig

load_dotenv()

create_folder("logs")
configure_logger("osinter")


config_options = FrontendConfig()
