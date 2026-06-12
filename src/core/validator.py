import logging
from pathlib import Path
from typing import Any, Dict, List

from pxr import Kind, Usd

logger = logging.getLogger(__name__)


class UsdValidator:

    def __init__(self, config: "ConfigManager"):
        self.config = config
        self._errors: List[str] = []

    def validate_asset(self, root_dir: Path, asset_name: str) -> bool:
        self._errors.clear()

        asset_dir = Path(root_dir).resolve() / asset_name
        logger.info(f"Staring structural validation of asset: '{asset_name}'")

        departments: Dict[str, Dict[str, str]] = self.config.get("pipeline.departments")
        root_prim_path = f"/{asset_name}"
        for department, data in departments.items():
            dir_name = data.get("dir_name", department)
            file_suffix = data.get("file_suffix", department)
            scope_name = data.get("scope_name", "geo")

            department_file = asset_dir / dir_name / f"{file_suffix}.usda"
            self._validate_stage(
                department_file, root_prim_path, department, scope_name
            )

        payload_file = asset_dir / f"{asset_name}_payload.usda"
        self._validate_payload(payload_file, departments)

        root_file = asset_dir / f"{asset_name}.usda"
        self._validate_root(root_file, root_prim_path, payload_file.name)

        if self._errors:
            logger.error(f"Asset '{asset_name}' is invalid. Found errors:")
            for error in self._errors:
                logger.error(f"\t\t{error}")
            return False

        logger.info(f"Asset '{asset_name}' is valid")
        return True

    def _validate_stage(
        self, file_path: Path, root_prim_path: str, department: str, scope: str
    ) -> None:
        if not file_path.exists():
            self._errors.append(f"File for '{department}' does not exist")
            return

        try:
            stage = Usd.Stage.Open(str(file_path))
            prim = stage.GetPrimAtPath(root_prim_path)

            if not prim:
                self._errors.append(
                    f"'{department}' file does not contain required root prim: '{root_prim_path}'"
                )
                return

            scope_path = f"{root_prim_path}/{scope}"
            if not stage.GetPrimAtPath(scope_path):
                self._errors.append(
                    f"'{department}' file does not contain required scope cointainer: '{scope}'"
                )

        except Exception as e:
            logger.error("Error opening USD file: {e}")
            self._errors.append("Internal error: could not read USD file")

    def _validate_payload(
        self, file_path: Path, departments: Dict[str, Dict[str, str]]
    ) -> None:
        if not file_path.exists():
            self._errors.append("Payload file not found")
            return

        try:
            stage = Usd.Stage.Open(str(file_path))
            layer = stage.GetRootLayer()
            sublayers = layer.subLayerPaths

            for department, data in departments.items():
                dir_name = data.get("dir_name", department)
                file_suffix = data.get("file_suffix", department)
                expected_sublayers = f"./{dir_name}/{file_suffix}.usda"

                if expected_sublayers not in sublayers:
                    self._errors.append(
                        f"Expected sublayers '{expected_sublayers}' not found"
                    )
        except Exception as e:
            logger.error(f"Error during payload reading: {e}")
            self._errors.append("Internal error: payload reading error")

    def _validate_root(
        self, file_path: Path, root_prim_path: str, payload_name: str
    ) -> None:
        if not file_path.exists():
            self._errors.append(f"Root file not found")
            return

        try:
            stage = Usd.Stage.Open(str(file_path))
            prim = stage.GetPrimAtPath(root_prim_path)

            if not prim:
                self._errors.append(f"Missing root prim: '{root_prim_path}'")
                return

            model_api = Usd.ModelAPI(prim)
            kind = model_api.GetKind()
            if kind != Kind.Tokens.component:
                self._errors.append(
                    f"Invalid 'kind' metadata. Expected type: 'component', found: '{kind}'"
                )

        except Exception as e:
            logger.error(f"Error during root file reading: {e}")
            self._errors.append("Internal error: root file reading error")
