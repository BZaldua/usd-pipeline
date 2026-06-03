import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.core import FolderStructure


class TestFolderStructure(unittest.TestCase):

    def setUp(self):
        self.mock_config_manager = MagicMock()
        self.mock_folders = {
            "camera": "cam_dir",
            "character": "char_dir",
            "environment": "env_dir",
            "light": "light_dir",
            "props": "prop_dir",
            "temp": "temp_dir",
        }

        def side_effect_get(key, default=None):
            if key == "asset_folders":
                return self.mock_folders
            return default

        self.mock_config_manager.get.side_effect = side_effect_get
        self.test_path = Path("/mock/base/path")

    @patch("pathlib.Path.mkdir")
    def test_init_and_bootstrap_folders(self, mock_mkdir):
        # Act
        fs = FolderStructure(self.test_path, config_manager=self.mock_config_manager)

        # Assert
        self.assertEqual(fs.output_path, self.test_path)
        self.assertEqual(fs.folders_to_create, self.mock_folders)
        self.assertEqual(mock_mkdir.call_count, len(self.mock_folders))
        
        expected_path = self.test_path / "cam_dir"
        mock_mkdir.assert_any_call(parents=True, exist_ok=True)

    @patch("pathlib.Path.mkdir")
    def test_get_methods(self, mock_mkdir):
        # Act
        fs = FolderStructure(self.test_path, config_manager=self.mock_config_manager)

        # Assert
        self.assertEqual(fs.get_cam(), self.test_path / "cam_dir")
        self.assertEqual(fs.get_char(), self.test_path / "char_dir")
        self.assertEqual(fs.get_env(), self.test_path / "env_dir")
        self.assertEqual(fs.get_light(), self.test_path / "light_dir")
        self.assertEqual(fs.get_prop(), self.test_path / "prop_dir")
        self.assertEqual(fs.get_temp(), self.test_path / "temp_dir")

    @patch("pathlib.Path.mkdir")
    def test_get_dir_names(self, mock_mkdir):
        # Act
        fs = FolderStructure(self.test_path, config_manager=self.mock_config_manager)

        # Assert
        self.assertEqual(fs.get_dir_names(), self.mock_folders)
