from pathlib import Path
from typing import Any, Dict

import yaml


class ConfigManager:

    def __init__(self, config_path: Path = None):
        self.config_path = config_path or (Path(__file__).parent.parent.parent
            / "resources"
            / "application.yaml"
        )
        self._config_data: Dict[str, Any] = {}
        self.reload()

    def reload(self) -> None:
        self._config_data = {
            "asset_folders": {
                "camera": "cam",
                "character": "char",
                "environment": "env",
                "light": "light",
                "props": "prop",
                "temp": "temp",
            }
        }

        if not self.config_path.exists():
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as stream:
                user_config = yaml.load(stream, Loader=yaml.SafeLoader)
                if user_config:
                    self._config_data.update(user_config)
        except Exception as e:
            raise ValueError(f"Error reading config YAML: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self._config_data.get(key, default)
