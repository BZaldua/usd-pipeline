import unittest
from functools import partial
from pathlib import Path
from unittest.mock import MagicMock, patch

from pxr import Usd

from src.config import ConfigManager
from src.core import DepartmentConfig, ProjectBootstrap

patch_usd_create = partial(patch, "src.core.bootstrap.Usd.Stage.CreateNew")
patch_usd_open = partial(patch, "src.core.bootstrap.Usd.Stage.Open")
patch_usd_get_stage = partial(
    patch, "src.core.bootstrap.ProjectBootstrap._get_or_create_stage"
)


class TestProjectBootstrap(unittest.TestCase):

    def setUp(self) -> None:
        self.mock_config = MagicMock(spec=ConfigManager)
        self.root_dir = Path("/tmp/mock_pipeline")
        self.asset_name = "test_asset"

        self.mock_yaml_data = {
            "model": {"dir_name": "model", "file_suffix": "model", "scope_name": "geo"},
            "look": {"dir_name": "look", "file_suffix": "look", "scope_name": "mtl"},
        }

    def test_load_departments_with_valid_config(self) -> None:
        # Arrange
        self.mock_config.get.return_value = self.mock_yaml_data

        # Act
        bootstrap = ProjectBootstrap(root_dir=self.root_dir, config=self.mock_config)

        # Assert
        self.assertIn("model", bootstrap.departments)
        self.assertIn("look", bootstrap.departments)

        model_config = bootstrap.departments["model"]
        self.assertIsInstance(model_config, DepartmentConfig)
        self.assertEqual(model_config.folder_name, "model")
        self.assertEqual(model_config.scope_name, "geo")

    def test_resolve_asset_paths(self) -> None:
        # Arrange
        self.mock_config.get.return_value = self.mock_yaml_data
        bootstrap = ProjectBootstrap(root_dir=self.root_dir, config=self.mock_config)

        # Act
        paths = bootstrap.resolve_asset_paths(self.asset_name)

        # Assert
        expected_asset_dir = self.root_dir / self.asset_name
        self.assertEqual(paths["asset_dir"], expected_asset_dir)
        self.assertEqual(
            paths["root_file"], expected_asset_dir / f"{self.asset_name}.usda"
        )

        self.assertEqual(paths["model_dir"], expected_asset_dir / "model")
        self.assertEqual(
            paths["model_file"], expected_asset_dir / "model" / "model.usda"
        )

    @patch.object(Path, "mkdir")
    @patch.object(Path, "exists")
    def test_create_directories_only_when_missing(
        self, mock_exists: MagicMock, mock_mkdir: MagicMock
    ) -> None:
        # Arrange
        self.mock_config.get.return_value = self.mock_yaml_data
        bootstrap = ProjectBootstrap(root_dir=self.root_dir, config=self.mock_config)

        mock_exists.side_effect = lambda: mock_exists.call_count == 1

        # Act
        paths = bootstrap.resolve_asset_paths(self.asset_name)
        bootstrap.create_directories(paths)

        # Assert
        self.assertTrue(mock_mkdir.called)

    @patch_usd_create()
    @patch_usd_open()
    @patch.object(Path, "exists")
    def test_get_or_create_stage_behavior(
        self, mock_exists: MagicMock, mock_open: MagicMock, mock_create_new: MagicMock
    ) -> None:
        # Arrange
        self.mock_config.get.return_value = self.mock_yaml_data
        bootstrap = ProjectBootstrap(root_dir=self.root_dir, config=self.mock_config)

        test_file = Path("/dummy/scene.usda")

        mock_exists.return_value = False

        # Act
        bootstrap._get_or_create_stage(test_file)

        # Assert
        mock_create_new.assert_called_once_with(str(test_file))
        mock_exists.return_value = True
        bootstrap._get_or_create_stage(test_file)
        mock_open.assert_called_once_with(str(test_file))

    @patch_usd_get_stage()
    @patch.object(ProjectBootstrap, "create_directories")
    def test_run_orchestrator_skips_if_prim_exists(
        self, mock_create_dirs: MagicMock, mock_get_stage: MagicMock
    ) -> None:
        # Arrange
        self.mock_config.get.return_value = self.mock_yaml_data
        bootstrap = ProjectBootstrap(root_dir=self.root_dir, config=self.mock_config)

        mock_stage = MagicMock(spec=Usd.Stage)
        mock_stage.GetPrimAtPath.return_value = True
        mock_get_stage.return_value = mock_stage

        # Act
        bootstrap.run(self.asset_name)

        # Assert
        mock_create_dirs.assert_called_once()
        self.assertFalse(mock_stage.GetRootLayer().Save.called)
