import logging
from pathlib import Path
from typing import Dict, NamedTuple, Union

from pxr import Kind, Usd, UsdGeom

logger = logging.getLogger(__name__)


class DepartmentConfig(NamedTuple):
    folder_name: str
    file_suffix: str
    scope_name: str


class ProjectBootstrap:

    def __init__(self, root_dir: Union[str, Path], config: "ConfigMapper"):
        self.root_dir = root_dir
        self.config = config
        self.departments: Dict[str, DepartmentConfig] = self._load_departments()

    def _load_departments(self) -> Dict[str, DepartmentConfig]:
        config_departments = self.config.get("pipeline.departments")

        return {
            str(dept_key): DepartmentConfig(
                folder_name=str(data.get("dir_name", dept_key)),
                file_suffix=str(data.get("file_suffix", dept_key)),
                scope_name=str(data.get("scope_name", "geo")),
            )
            for dept_key, data in config_departments.items()
        }

    def resolve_asset_paths(self, asset_name: str) -> Dict[str, Path]:
        asset_dir = self.root_dir / asset_name

        paths = {
            "asset_dir": asset_dir,
            "root_file": asset_dir / f"{asset_name}.usda",
            "payload_file": asset_dir / f"{asset_name}_payload.usda",
        }

        for dept_key, config in self.departments.items():
            dept_dir = asset_dir / config.folder_name
            paths[f"{dept_key}_dir"] = dept_dir
            paths[f"{dept_key}_file"] = dept_dir / f"{config.file_suffix}.usda"

        return paths

    def create_directories(self, paths: Dict[str, Path]) -> None:
        dir_paths = {k: v for k, v in paths.items() if k.endswith("_dir")}
        for dir_path in dir_paths.values():
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Directory successfully created: {dir_path}")

    @staticmethod
    def _get_or_create_stage(file_path: Path) -> Usd.Stage:
        if file_path.exists():
            return Usd.Stage.Open(str(file_path))
        return Usd.Stage.CreateNew(str(file_path))

    def _bootstrap_department_stage(
        self, file_path: Path, root_prim_path: str, scope_name: str
    ) -> None:
        stage = self._get_or_create_stage(file_path)
        if not stage.GetPrimAtPath(root_prim_path):
            prim = UsdGeom.Xform.Define(stage, root_prim_path)
            stage.SetDefaultPrim(prim.GetPrim())
            UsdGeom.Scope.Define(stage, f"{root_prim_path}/{scope_name}")
            stage.GetRootLayer().Save()

    def run(self, asset_name: str) -> None:
        paths = self.resolve_asset_paths(asset_name)
        self.create_directories(paths)

        root_prim_path = f"/{asset_name}"

        for dept_key, config in self.departments.items():
            self._bootstrap_department_stage(
                file_path=paths[f"{dept_key}_file"],
                root_prim_path=root_prim_path,
                scope_name=config.scope_name,
            )

        payload_stage = self._get_or_create_stage(paths["payload_file"])
        if not payload_stage.GetPrimAtPath(root_prim_path):
            payload_prim = payload_stage.DefinePrim(root_prim_path)
            payload_stage.SetDefaultPrim(payload_prim)

            payload_layer = payload_stage.GetRootLayer()
            payload_layer.subLayerPaths.clear()

            for dept_key in ["look", "model"]:
                if dept_key in self.departments:
                    config = self.departments[dept_key]
                    relative_path = (
                        f"./{config.folder_name}/{paths[f'{dept_key}_file'].name}"
                    )
                    payload_layer.subLayerPaths.append(relative_path)

            payload_layer.Save()

        root_stage = self._get_or_create_stage(paths["root_file"])
        if not root_stage.GetPrimAtPath(root_prim_path):
            root_prim = root_stage.DefinePrim(root_prim_path)
            root_stage.SetDefaultPrim(root_prim)

            Usd.ModelAPI(root_prim).SetKind(Kind.Tokens.component)

            root_prim.GetPayloads().ClearPayloads()
            root_prim.GetPayloads().AddPayload(
                assetPath=f"./{paths['payload_file'].name}", primPath=root_prim_path
            )
            root_stage.GetRootLayer().Save()
            logger.info(
                f"Bootstrap processed finished successfully for: '{asset_name}'"
            )
