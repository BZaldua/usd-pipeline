import tempfile
import unittest
from pathlib import Path

from src.core import FolderStructure


class TestFolderStructure(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.output_path = Path(self.test_dir.name) / "output"
        self.fs = FolderStructure(str(self.output_path))

    def tearDown(self):
        self.test_dir.cleanup()

    def test_bootstrap_folders_creates_all_directories(self):
        for dir_name in self.fs.get_dir_names():
            subfolder = self.output_path / dir_name
            self.assertTrue(subfolder.exists())

    def test_getters_return_correct_paths(self):
        self.assertEqual(self.fs.get_cam(), self.output_path / "cam")
        self.assertEqual(self.fs.get_char(), self.output_path / "char")
        self.assertEqual(self.fs.get_env(), self.output_path / "env")
        self.assertEqual(self.fs.get_prop(), self.output_path / "prop")
        self.assertEqual(self.fs.get_temp(), self.output_path / "temp")
        self.assertEqual(self.fs.get_light(), self.output_path / "light")

    def test_get_dir_names_returns_tuple(self):
        names = self.fs.get_dir_names()
        self.assertIsInstance(names, tuple)
        self.assertEqual(len(names), 6)
