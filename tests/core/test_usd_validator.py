import tempfile
import unittest
from pathlib import Path

from pxr import Usd

from src.core import UsdValidator


class TestUSDValidator(unittest.TestCase):

    def setUp(self):
        self.validator = UsdValidator(None)
        self.test_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.test_dir.name)

    def tearDown(self):
        self.test_dir.cleanup()

    def test_validate_missing_default_prim(self):
        # Arrange
        usd_path = self.base_path / "test_broken.usda"
        stage = Usd.Stage.CreateNew(str(usd_path))
        stage.DefinePrim("/Character", "Xform")
        stage.Save()

        # Act
        report = self.validator.validate_file(usd_path)

        # Assert
        self.assertFalse(report["is_valid"])
        self.assertIn("Default prim not defined in Stage", report["errors"][0])

    def test_validate_correct_usd(self):
        # Arrange
        usd_path = self.base_path / "test_correct.usda"
        stage = Usd.Stage.CreateNew(str(usd_path))
        prim = stage.DefinePrim("/Character", "Xform")

        stage.SetDefaultPrim(prim)
        stage.Save()

        # Act
        report = self.validator.validate_file(usd_path)

        # Assert
        self.assertTrue(report["is_valid"])
        self.assertEqual(len(report["errors"]), 0)
