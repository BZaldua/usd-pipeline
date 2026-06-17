import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

from pxr import Kind, Sdf, Usd, UsdGeom

logger = logging.getLogger(__name__)


class UsdValidator:

    def __init__(self, config: "ConfigManager"):
        self.config = config
        self._errors: List[str] = []
        self._warnings: List[str] = []
        self._default_root_ext = "usd"
        self._version_pattern = re.compile(
            r"^([a-zA-Z0-9_]+)_([a-zA-Z0-9]+)_v(\d{3,4})\.(usdc|usda|usd)$"
        )

    def _find_latest_department_version(
        self, dept_dir: Path, asset_name: str, department_type: str
    ) -> Optional[Path]:
        if not dept_dir.exists():
            return None

        highest_version = -1
        latest_file: Optional[Path] = None

        for file_path in dept_dir.iterdir():
            if file_path.is_dir():
                continue

            if file_path.name.startswith("."):
                continue

            match = self._version_pattern.match(file_path.name)
            if not match:
                self._warnings.append(
                    f"[{department_type}] File with unsupported name/format: '{file_path.name}'. Delete if not required."
                )
                continue

            file_asset, file_type, version_str, file_ext = match.groups()
            if file_asset != asset_name or file_type != department_type:
                continue

            version_num = int(version_str)
            if version_num > highest_version:
                highest_version = version_num
                latest_file = file_path

        return latest_file

    def validate_asset(self, root_dir: Path, asset_name: str) -> bool:
        self._errors.clear()

        asset_dir = Path(root_dir).resolve() / asset_name
        layers_dir = asset_dir / "layers"

        logger.info(f"Staring validation for asset: '{asset_name}'")

        departments: Dict[str, Dict[str, str]] = self.config.get("pipeline.departments")
        root_prim_path = f"/{asset_name}"

        resolved_dept_files: Dict[str, Path] = {}

        for department, data in departments.items():
            dir_name = data.get("dir_name", department)
            scope_name = data.get("scope_name", "geo")
            expected_format = data.get("format", "usd")

            dept_base_dir = layers_dir / dir_name
            dept_file = self._find_latest_department_version(
                dept_base_dir, asset_name, department
            )

            if not dept_file:
                self._errors.append(
                    f"[{department}] No version found for '{asset_name}_{department}'"
                )
                continue

            if dept_file.suffix != f".{expected_format}":
                self._errors.append(f"[{department}] Invalid file format found")

            resolved_dept_files[department] = dept_file

            self._validate_department_layer(
                dept_file, root_prim_path, department, scope_name
            )

            if department == "model":
                self._validate_model_structure(dept_file, root_prim_path)

        payload_file = asset_dir / f"{asset_name}_payload.{self._default_root_ext}"
        self._validate_payload(payload_file, departments, resolved_dept_files)

        root_file = asset_dir / f"{asset_name}.{self._default_root_ext}"
        self._validate_root(root_file, root_prim_path)

        if root_file.exists() and not self._errors:
            self._validate_stage_content(root_file)

        if self._errors:
            logger.error(f"Asset '{asset_name}' is INVALID. Errors:")
            for error in self._errors:
                logger.error(f"\t{error}")
            return False

        logger.info(f"Asset '{asset_name}' is OK")
        return True

    def _validate_department_layer(
        self, file_path: Path, root_prim_path: str, department: str, scope: str
    ) -> None:
        try:
            layer = Sdf.Layer.FindOrOpen(str(file_path))
            if not layer:
                self._errors.append(f"[{department}] USD file is empty or corrupt")
                return

            if not layer.GetPrimAtPath(root_prim_path):
                self._errors.append(
                    f"[{department}] Required root prim is missing: '{root_prim_path}'"
                )
                return

            scope_path = f"{root_prim_path}/{scope}"
            if not layer.GetPrimAtPath(scope_path):
                self._errors.append(
                    f"[{department}] Scope container is missing: '{scope_path}'"
                )
        except Exception as e:
            self._errors.append(f"[{department}] Error reading internal layer: {e}")

    def _validate_model_structure(self, file_path: Path, root_prim_path: str) -> None:
        try:
            layer = Sdf.Layer.FindOrOpen(str(file_path))

            def _traverse_spec(prim_spec):
                if prim_spec.typeName in ["Material", "Shader", "Camera"]:
                    self._errors.append(
                        f"[Model] Forbidden element '{prim_spec.typeName}' in model: '{prim_spec.path}'"
                    )

                if prim_spec.typeName == "Mesh":
                    points = prim_spec.attributes.get("points")
                    if not points or not points.default or len(points.default) == 0:
                        self._errors.append(
                            f"[Model] Geo mesh with no vertices in: '{prim_spec.path}'"
                        )

                for child in prim_spec.nameChildren:
                    _traverse_spec(child)

            root_spec = layer.GetPrimAtPath(root_prim_path)
            if root_spec:
                _traverse_spec(root_spec)
        except Exception as e:
            self._errors.append(f"[Model] Topological analysis error: {e}")

    def _validate_payload(
        self,
        file_path: Path,
        departments: Dict[str, Dict[str, str]],
        resolved_files: Dict[str, Path],
    ) -> None:
        if not file_path.exists():
            self._errors.append(f"Payload file not found: {file_path.name}")
            return

        try:
            layer = Sdf.Layer.FindOrOpen(str(file_path))
            sublayers = layer.subLayerPaths

            for department, data in departments.items():
                dir_name = data.get("dir_name", department)

                if department in resolved_files:
                    actual_file_name = resolved_files[department].name
                    expected_sublayer = f"./layers/{dir_name}/{actual_file_name}"

                    if expected_sublayer not in sublayers:
                        self._errors.append(
                            f"[Payload] The assembly file is not calling correct version of {department}. Expected to find: '{expected_sublayer}'"
                        )
                else:
                    self._errors.append(
                        f"[Payload] Unable to verify sublayer of '{department}' because file does not exist"
                    )
        except Exception as e:
            self._errors.append(f"Internal error: payload reading error: {e}")

    def _validate_root(self, file_path: Path, root_prim_path: str) -> None:
        if not file_path.exists():
            self._errors.append(f"Master root file not found: {file_path.name}")
            return

        try:
            layer = Sdf.Layer.FindOrOpen(str(file_path))
            prim_spec = layer.GetPrimAtPath(root_prim_path)
            if not prim_spec or prim_spec.kind != Kind.Tokens.component:
                self._errors.append(
                    f"[Root] missing or invalid 'kind' in: '{root_prim_path}'"
                )
        except Exception as e:
            self._errors.append(f"Internal error: root file reading error: {e}")

    def _validate_stage_content(self, root_file: Path) -> None:
        try:
            stage = Usd.Stage.Open(str(root_file))
            for prim in stage.Traverse():
                if prim.IsA(UsdGeom.Mesh):
                    primvars_api = UsdGeom.PrimvarsAPI(prim)
                    if not primvars_api.HasPrimvar(
                        "st"
                    ) and not primvars_api.HasPrimvar("uv"):
                        logger.warning(
                            f"[Content - UV] {prim.GetPath()} does not contain texture coordinates"
                        )
        except Exception as e:
            self._errors.append(f"[Content] Critical error analyzing Stage: {e}")
