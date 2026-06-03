import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.core import FolderStructure


class TestFolderStructure(unittest.TestCase):

    def setUp(self):
        self.patcher_config = patch("src.core.folder_structure.ConfigManager")
        self.mock_config_class = self.patcher_config.start()

        self.mock_config_instance = MagicMock()
        self.mock_config_class.return_value = self.mock_config_instance

        self.mock_folders = {
            "camera": "cam_dir",
            "character": "char_dir",
            "environment": "env_dir",
            "light": "light_dir",
            "props": "prop_dir",
            "temps": "temp_dir",
        }

        def side_effect_get(key):
            if key == "asset_folders":
                return self.mock_folders
            return f"mocked_{key.split('.')[-1]}"

        self.mock_config_instance.get.side_effect = side_effect_get

        self.test_path = Path("/mock/base/path")

    def tearDown(self):
        self.patcher_config.stop()

    @patch("pathlib.Path.mkdir")
    def test_init_and_bootstrap_folders(self, mock_mkdir):
        # Act
        fs = FolderStructure(self.test_path)

        # Assert
        self.assertEqual(fs.output_path, self.test_path)
        self.assertEqual(fs.folders_to_create, self.mock_folders)
        self.assertEqual(mock_mkdir.call_count, len(self.mock_folders))

    @patch("pathlib.Path.mkdir")
    def test_get_methods(self, mock_mkdir):
        # Act
        fs = FolderStructure(self.test_path)

        # Assert
        self.assertEqual(fs.get_cam(), self.test_path / "mocked_camera")
        self.assertEqual(fs.get_char(), self.test_path / "mocked_character")
        self.assertEqual(fs.get_env(), self.test_path / "mocked_environment")
        self.assertEqual(fs.get_light(), self.test_path / "mocked_light")
        self.assertEqual(fs.get_prop(), self.test_path / "mocked_props")
        self.assertEqual(fs.get_temp(), self.test_path / "mocked_temps")

    @patch("pathlib.Path.mkdir")
    def test_get_dir_names(self, mock_mkdir):
        # Act
        fs = FolderStructure(self.test_path)

        # Assert
        self.assertEqual(fs.get_dir_names(), self.mock_folders)
