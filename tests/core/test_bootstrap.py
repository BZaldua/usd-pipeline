import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from pxr import Kind, Usd

from usd_pipeline_core.core import ProjectBootstrap


class TestProjectBootstrap(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root_dir = Path(self.temp_dir.name)

        self.mock_config = MagicMock()
        self.mock_config.get.return_value = {
            "model": {"dir_name": "model", "scope_name": "geo", "format": "usdc"},
            "look": {"dir_name": "look", "scope_name": "mtl", "format": "usda"},
            "rig": {"dir_name": "rig", "scope_name": "rig", "format": "usdc"},
        }

        self.bootstrap = ProjectBootstrap(
            root_dir=self.root_dir, config=self.mock_config
        )
        self.asset_name = "test_asset"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_load_departments(self):
        self.assertIn("model", self.bootstrap.departments)
        self.assertIn("look", self.bootstrap.departments)

        model_config = self.bootstrap.departments["model"]
        self.assertEqual(model_config.folder_name, "model")
        self.assertEqual(model_config.scope_name, "geo")
        self.assertEqual(model_config.internal_format, "usdc")

    def test_resolve_asset_paths(self):
        # Act
        paths = self.bootstrap.resolve_asset_paths(self.asset_name, version=3)

        # Assert
        expected_root = self.root_dir / self.asset_name
        self.assertEqual(paths["asset_dir"], expected_root)
        self.assertEqual(paths["root_file"], expected_root / f"{self.asset_name}.usd")
        self.assertEqual(
            paths["payload_file"], expected_root / f"{self.asset_name}_payload.usd"
        )

        expected_versioned_file = (
            expected_root / "layers" / "model" / f"{self.asset_name}_model_v003.usdc"
        )
        self.assertEqual(paths["model_versioned_file"], expected_versioned_file)

    def test_create_directories(self):
        # Arrange
        paths = self.bootstrap.resolve_asset_paths(self.asset_name, version=1)

        # Act
        self.bootstrap.create_directories(paths)

        # Assert
        self.assertTrue(paths["asset_dir"].exists())
        self.assertTrue(paths["layers_dir"].exists())
        self.assertTrue(paths["model_dir"].exists())
        self.assertTrue(paths["look_dir"].exists())

    def test_get_or_create_stage_format(self):
        # Arrange
        test_file = self.root_dir / "test_format.usd"

        # Act
        stage = self.bootstrap._get_or_create_stage(test_file, internal_format="usdc")
        layer = stage.GetRootLayer()

        # Assert
        file_args = layer.GetFileFormatArguments()
        self.assertEqual(file_args.get("format"), "usdc")

    def test_run_generates_valid_usd_structure(self):
        # Arrange
        version = 1

        # Act
        self.bootstrap.run(self.asset_name, version=version)
        paths = self.bootstrap.resolve_asset_paths(self.asset_name, version=version)

        # Assert
        self.assertTrue(paths["root_file"].exists())
        self.assertTrue(paths["payload_file"].exists())
        self.assertTrue(paths["model_file"].exists())
        self.assertTrue(paths["model_versioned_file"].exists())

        root_stage = Usd.Stage.Open(str(paths["root_file"]))
        root_prim = root_stage.GetPrimAtPath(f"/{self.asset_name}")

        self.assertTrue(root_prim.IsValid())
        self.assertEqual(root_prim.GetTypeName(), "Xform")

        self.assertEqual(Usd.ModelAPI(root_prim).GetKind(), Kind.Tokens.component)

        self.assertEqual(root_stage.GetDefaultPrim(), root_prim)

        payload_stage = Usd.Stage.Open(str(paths["payload_file"]))
        payload_layer = payload_stage.GetRootLayer()

        expected_sublayers = [
            f"./layers/model/{paths['model_file'].name}",
            f"./layers/look/{paths['look_file'].name}",
            f"./layers/rig/{paths['rig_file'].name}",
        ]
        self.assertEqual(list(payload_layer.subLayerPaths), expected_sublayers)

        model_stage = Usd.Stage.Open(str(paths["model_versioned_file"]))
        scope_prim = model_stage.GetPrimAtPath(f"/{self.asset_name}/geo")

        self.assertTrue(scope_prim.IsValid())
        self.assertEqual(scope_prim.GetTypeName(), "Scope")
