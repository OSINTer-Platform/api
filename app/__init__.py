from modules.config import FrontendConfig, configure_logger
from modules.misc import create_folder

create_folder("logs")
configure_logger("osinter")

config_options = FrontendConfig()
