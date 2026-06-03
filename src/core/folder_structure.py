import logging
from pathlib import Path
from typing import Tuple

from src.config import ConfigManager

logger = logging.getLogger(__name__)


class FolderStructure:

    def __init__(self, context_path: Path = None):
        self.output_path = context_path
        self.config = ConfigManager()
        self.folders_to_create = self.config.get("asset_folders")
        self.bootstrap_folders()

    def bootstrap_folders(self) -> None:
        logger.info("Creating folders...")
        for k, dir_name in self.folders_to_create.items():
            full_path = self.output_path / dir_name
            logger.debug(f"Creating for {k} folder: {full_path}")
            full_path.mkdir(parents=True, exist_ok=True)
        logger.info("Folders created")

    def get_cam(self) -> str:
        return self.output_path / self.config.get("assets_folder.camera")

    def get_char(self) -> str:
        return self.output_path / self.config.get("assets_folder.character")

    def get_env(self) -> str:
        return self.output_path / self.config.get("assets_folder.environment")

    def get_light(self) -> str:
        return self.output_path / self.config.get("assets_folder.light")

    def get_prop(self) -> str:
        return self.output_path / self.config.get("assets_folder.props")

    def get_temp(self) -> str:
        return self.output_path / self.config.get("assets_folder.temps")

    def get_dir_names(self) -> Tuple:
        return self.folders_to_create
