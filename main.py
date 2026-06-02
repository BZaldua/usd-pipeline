import argparse
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
        print(f"[ERROR] Config file not found at: {config_path}")
        return

    ConfigManager(config_path)

if __name__ == "__main__":
    main()

    output_path = Path("./output")
    FolderStructure(output_path)
