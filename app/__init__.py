from dotenv import load_dotenv

from modules.config import FrontendConfig, configure_logger
from modules.misc import create_folder

load_dotenv()

create_folder("logs")
configure_logger("osinter")

config_options = FrontendConfig()
