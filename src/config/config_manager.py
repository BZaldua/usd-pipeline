import logging
import logging.config
from pathlib import Path
from typing import Any, Dict, Type

import yaml


class ConfigManager:

    def __init__(self, config_path: Path = None):
        self.config_path = config_path or (
            Path(__file__).parent.parent.parent / "resources" / "application.yaml"
        )
        self._config_data: Dict[str, Any] = {}
        self.reload()

    def reload(self) -> None:
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
        if "." not in key:
            return self._config_data.get(key, default)

        parts = key.split(".")
        current_data = self._config_data

        for part in parts:
            if isinstance(current_data, dict) and part in current_data:
                current_data = current_data[part]
            else:
                return default

        return current_data

    def setup_logging(self, qt_handler_class: Type[logging.Handler] = None) -> Any:
        log_config = self.get("logging")

        if log_config:
            if (
                qt_handler_class
                and "handlers" in log_config
                and "qt_console" in log_config["handlers"]
            ):
                log_config["handlers"]["qt_console"]["()"] = qt_handler_class

            logging.config.dictConfig(log_config)
        else:
            logging.basicConfig(level=logging.INFO)

        if qt_handler_class:
            root_logger = logging.getLogger()
            for handler in root_logger.handlers:
                if isinstance(handler, qt_handler_class):
                    return handler

        return None
