import logging
from pathlib import Path
from typing import Any, Dict

from pxr import Sdf, Usd

logger = logging.getLogger(__name__)


class UsdValidator:

    def __init__(self, config_manager: "ConfigManager"):
        self.config = config_manager
        self.supported_formats = [".usd", ".usda", ".usdc"]

    def validate_file(self, file_path: Path) -> Dict[str, Any]:
        report_template = {"file": str(file_path), "is_valid": True, "errors": []}

        if not file_path.exists():
            report_template["is_valid"] = False
            report_template["errors"].append("File not found")
            return report_template

        if file_path.suffix.lower() not in self.supported_formats:
            report_template["is_valid"] = False
            report_template["errors"].append(
                f"Unsupported file format: {file_path.suffix}"
            )
            return report_template

        stage = Usd.Stage.Open(str(file_path))

        # Stage validation
        valid_stage = self._validate_stage(stage, report_template)
        if not valid_stage:
            return report_template

        # Stage > DefaultPrim validation
        valid_prim = self._validate_prim(stage.GetDefaultPrim(), report_template)
        if not valid_prim:
            return report_template

        # Stage > RootLayer validation
        _ = self._validate_layer(stage.GetRootLayer(), report_template)

        return report_template

    def _validate_stage(self, stage: Usd.Stage, report: Dict[str, Any]) -> bool:
        if not stage:
            report["is_valid"] = False
            report["errors"].append("USD file cannot be opened")
            return False

        if not stage.HasDefaultPrim():
            report["is_valid"] = False
            report["errors"].append("Default prim not defined in Stage")
            return False

        return True

    def _validate_prim(self, prim: Usd.Prim, report: Dict[str, Any]) -> bool:
        if prim.GetName().isidentifier():
            return True

        report["is_valid"] = False
        report["errors"].append(f"Prim `{prim.GetName()}` has unsupported properties")
        return False

    def _validate_layer(self, layer: Sdf.Layer, report: Dict[str, Any]) -> bool:
        for sublayer_path in layer.subLayerPaths:
            if Path(sublayer_path).is_absolute():
                report["is_valid"] = False
                report["errors"].append(
                    f"Sublayer `{sublayer_path}` has an absolute path. Relative expected"
                )
                return False
        return True
