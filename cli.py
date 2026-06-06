import argparse
import logging
import logging.config
from pathlib import Path
from src.core import ProjectBootstrap
from src.config import ConfigManager
import sys

logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(
        description="OpenUSD file bootstrap and validator"
    )
    
    parser.add_argument(
        "-c", "--config",
        required=False,
        type=str,
        help="Absolute path to config file"
    )
    

    args = parser.parse_args()

    config_path = Path(args.config) if args.config else None
    config = ConfigManager(config_path)

    log_config = config.get("logging")
    if log_config:
        logging.config.dictConfig(log_config)
    else:
        logging.basicConfig(level=logging.INFO)


    PRODUCTION_ASSETS_DIR = Path("./output/assets")
    NEW_ASSET_NAME = "prop_chair"

    bootstrap = ProjectBootstrap(PRODUCTION_ASSETS_DIR, config)
    bootstrap.run(NEW_ASSET_NAME)


if __name__ == "__main__":
    main()
