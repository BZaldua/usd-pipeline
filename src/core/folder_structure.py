from pathlib import Path
from typing import Tuple
from src.config import ConfigManager


class FolderStructure:

    def __init__(self, context_path: Path = None):
        self.output_path = context_path
        self.config = ConfigManager()
        self.folders_to_create = self.config.get("asset_folders")
        self.bootstrap_folders()
        
    def bootstrap_folders(self) -> None:
        print("[INFO] Creating folders...")
        for dir_name in self.folders_to_create:
            full_path = (self.output_path / dir_name)
            print(f"[DEBUG] Creating folder: {full_path}")
            full_path.mkdir(parents=True, exist_ok=True)
        print("[INFO] Folders created")

    def get_cam(self) -> str:
        return self.output_path / "cam"

    def get_char(self) -> str:
        return self.output_path / "char"

    def get_env(self) -> str:
        return self.output_path / "env"

    def get_light(self) -> str:
        return self.output_path / "light"

    def get_prop(self) -> str:
        return self.output_path / "prop"

    def get_temp(self) -> str:
        return self.output_path / "temp"

    def get_dir_names(self) -> Tuple:
        return self._DIR_NAMES
