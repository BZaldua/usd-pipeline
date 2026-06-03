import argparse
import logging
import logging.config
from pathlib import Path
from src.config import ConfigManager
from src.core import FolderStructure

def main():
    parser = argparse.ArgumentParser(
        description="Herramienta de Inicialización de Proyectos VFX / OpenUSD."
    )
    
    parser.add_argument(
        "-c", "--config",
        required=True,
        type=str,
        help="Absolute path to config file"
    )
    

    args = parser.parse_args()

    config_path = Path(args.config) if args.config else None
    if not config_path.is_file():
        raise FileNotFoundError(f"Config file not found at {config_path}")
    
    config = ConfigManager(config_path)

    log_config = config.get("logging")
    if log_config:
        logging.config.dictConfig(log_config)
    else:
        logging.basicConfig(level=logging.INFO)


if __name__ == "__main__":
    main()

    output_path = Path("./output")
    FolderStructure(output_path)
