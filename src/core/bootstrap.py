import logging
from pathlib import Path
from typing import Dict, NamedTuple, Union

from pxr import Kind, Sdf, Usd, UsdGeom

logger = logging.getLogger(__name__)


class DepartmentConfig(NamedTuple):
    folder_name: str
    scope_name: str
    internal_format: str


class ProjectBootstrap:

    def __init__(self, root_dir: Union[str, Path], config: "ConfigMapper"):
        self.root_dir = Path(root_dir)
        self.config = config
        self.departments: Dict[str, DepartmentConfig] = self._load_departments()

    def _load_departments(self) -> Dict[str, DepartmentConfig]:
        config_departments = self.config.get("pipeline.departments")

        return {
            str(dept_key): DepartmentConfig(
                folder_name=str(data.get("dir_name", dept_key)),
                scope_name=str(data.get("scope_name", "geo")),
                internal_format=str(data.get("format", "usdc")),
            )
            for dept_key, data in config_departments.items()
        }

    def resolve_asset_paths(self, asset_name: str, version: int = 1) -> Dict[str, Path]:
        asset_dir = self.root_dir / asset_name
        layers_dir = asset_dir / "layers"

        version_str = f"v{version:03d}"

        paths = {
            "asset_dir": asset_dir,
            "layers_dir": layers_dir,
            "root_file": asset_dir / f"{asset_name}.usd",
            "payload_file": asset_dir / f"{asset_name}_payload.usd",
        }

        for dept_key, config in self.departments.items():
            dept_dir = layers_dir / config.folder_name
            ext = config.internal_format

            paths[f"{dept_key}_dir"] = dept_dir
            paths[f"{dept_key}_file"] = dept_dir / f"{config.folder_name}.usd"
            paths[f"{dept_key}_versioned_file"] = (
                dept_dir / f"{asset_name}_{config.folder_name}_{version_str}.{ext}"
            )

        return paths

    def create_directories(self, paths: Dict[str, Path]) -> None:
        dir_paths = {k: v for k, v in paths.items() if k.endswith("_dir")}
        for dir_path in dir_paths.values():
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Directorio creado: {dir_path}")

    @staticmethod
    def _get_or_create_stage(file_path: Path, internal_format: str = None) -> Usd.Stage:
        if file_path.exists():
            return Usd.Stage.Open(str(file_path))

        target_path = str(file_path)

        if internal_format in ["usda", "usdc"]:
            layer = Sdf.Layer.CreateNew(target_path, args={"format": internal_format})
            if layer:
                return Usd.Stage.Open(layer)

        return Usd.Stage.CreateNew(target_path)

    def _bootstrap_department_stage(
        self,
        paths: Dict[str, Path],
        dept_key: str,
        root_prim_path: str,
        config: DepartmentConfig,
    ) -> None:
        versioned_path = paths[f"{dept_key}_versioned_file"]
        master_path = paths[f"{dept_key}_file"]

        v_stage = self._get_or_create_stage(
            versioned_path, internal_format=config.internal_format
        )
        if not v_stage.GetPrimAtPath(root_prim_path):
            prim = UsdGeom.Xform.Define(v_stage, root_prim_path)
            v_stage.SetDefaultPrim(prim.GetPrim())
            UsdGeom.Scope.Define(v_stage, f"{root_prim_path}/{config.scope_name}")
            v_stage.GetRootLayer().Save()

        m_stage = self._get_or_create_stage(master_path, internal_format="usda")
        m_layer = m_stage.GetRootLayer()

        m_layer.subLayerPaths.clear()
        relative_versioned_path = f"./{versioned_path.name}"
        m_layer.subLayerPaths.append(relative_versioned_path)

        if not m_stage.GetPrimAtPath(root_prim_path):
            m_prim = m_stage.OverridePrim(root_prim_path)
            m_stage.SetDefaultPrim(m_prim)

        m_layer.Save()

    def run(self, asset_name: str, version: int = 1) -> None:
        paths = self.resolve_asset_paths(asset_name, version=version)
        self.create_directories(paths)

        root_prim_path = f"/{asset_name}"

        for dept_key, config in self.departments.items():
            self._bootstrap_department_stage(
                paths=paths,
                dept_key=dept_key,
                root_prim_path=root_prim_path,
                config=config,
            )

        payload_stage = self._get_or_create_stage(
            paths["payload_file"], internal_format="usda"
        )
        payload_layer = payload_stage.GetRootLayer()
        payload_layer.subLayerPaths.clear()

        for dept_key in self.departments.keys():
            config = self.departments[dept_key]
            relative_path = (
                f"./layers/{config.folder_name}/{paths[f'{dept_key}_file'].name}"
            )
            payload_layer.subLayerPaths.append(relative_path)

        if not payload_stage.GetPrimAtPath(root_prim_path):
            payload_prim = payload_stage.OverridePrim(root_prim_path)
            payload_stage.SetDefaultPrim(payload_prim)

        payload_layer.Save()

        root_stage = self._get_or_create_stage(
            paths["root_file"], internal_format="usda"
        )

        if not root_stage.GetPrimAtPath(root_prim_path):
            root_prim = root_stage.DefinePrim(root_prim_path)
            root_stage.SetDefaultPrim(root_prim)

            Usd.ModelAPI(root_prim).SetKind(Kind.Tokens.component)

            root_prim.GetPayloads().ClearPayloads()
            root_prim.GetPayloads().AddPayload(
                assetPath=f"./{paths['payload_file'].name}", primPath=root_prim_path
            )
            root_stage.GetRootLayer().Save()
            logger.info(f"Bootstrap process finished for: '{asset_name}' v({version})")
