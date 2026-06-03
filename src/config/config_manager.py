from pathlib import Path
from typing import Any, Dict

import yaml


class ConfigManager:

    _instance = None
    _config_data: Dict[str, Any] = {}
    _loaded: bool = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, config_path: Path = None):
        if not self._loaded:
            if not config_path:
                config_path = (
                    Path(__file__).parent.parent.parent
                    / "resources"
                    / "application.yaml"
                )
            self._load_yaml(config_path)

    def _load_yaml(self, config_path: Path) -> None:
        self._config_data = {
            "asset_folders": ["cam", "char", "env", "light", "prop", "temp"]
        }

        if not config_path.exists():
            self._loaded = True
            return

        try:
            with open(config_path, "r", encoding="utf-8") as stream:
                user_config = yaml.load(stream, Loader=yaml.SafeLoader)
                if user_config:
                    self._config_data.update(user_config)
        except Exception as e:
            raise ValueError(f"Error reading config YAML: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self._config_data.get(key, default)
