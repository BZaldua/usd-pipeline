import logging
from pathlib import Path
from typing import Dict, Tuple

logger = logging.getLogger(__name__)


class FolderStructure:

    def __init__(self, context_path: Path, config_manager: "ConfigManager"):
        self.output_path = context_path
        self.config = config_manager
        self.folders_to_create: Dict[str, str] = self.config.get("asset_folders")
        self.bootstrap_folders()

    def bootstrap_folders(self) -> None:
        logger.info("Creating folders...")
        for k, dir_name in self.folders_to_create.items():
            full_path = self.output_path / dir_name
            logger.debug(f"Creating for {k} folder: {full_path}")
            full_path.mkdir(parents=True, exist_ok=True)
        logger.info("Folders created")

    def get_cam(self) -> str:
        return self.output_path / self.folders_to_create.get("camera")

    def get_char(self) -> str:
        return self.output_path / self.folders_to_create.get("character")

    def get_env(self) -> str:
        return self.output_path / self.folders_to_create.get("environment")

    def get_light(self) -> str:
        return self.output_path / self.folders_to_create.get("light")

    def get_prop(self) -> str:
        return self.output_path / self.folders_to_create.get("props")

    def get_temp(self) -> str:
        return self.output_path / self.folders_to_create.get("temp")

    def get_dir_names(self) -> Tuple:
        return self.folders_to_create
