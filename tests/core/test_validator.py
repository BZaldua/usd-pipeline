import unittest
from functools import partial
from pathlib import Path
from unittest.mock import MagicMock, patch

from pxr import Kind, Sdf, Usd

from src.core import UsdValidator

MODULE_PATH = "src.core.validator"
patch_usd_open = partial(patch, f"{MODULE_PATH}.Usd.Stage.Open")


class TestUsdValidator(unittest.TestCase):

    def setUp(self) -> None:
        self.mock_config = MagicMock()
        self.root_dir = Path("/mock/pipeline/assets")
        self.asset_name = "prop_mesa"

        # Datos simulados idénticos a la estructura real de tu YAML
        self.mock_departments_data = {
            "model": {"dir_name": "model", "file_suffix": "model", "scope_name": "geo"},
            "look": {"dir_name": "look", "file_suffix": "look", "scope_name": "ml"},
        }
        self.mock_config.get.return_value = self.mock_departments_data

        # Instancia de la clase bajo prueba pasándole el mock posicionalmente
        self.validator = UsdValidator(self.mock_config)

    @patch_usd_open()
    @patch.object(Path, "exists")
    def test_validate_asset_success_flow(
        self, mock_exists: MagicMock, mock_stage_open: MagicMock
    ) -> None:
        # Arrange
        mock_exists.return_value = True
        mock_stage = MagicMock(spec=Usd.Stage)
        mock_prim = MagicMock(spec=Usd.Prim)
        mock_layer = MagicMock(spec=Sdf.Layer)
        mock_stage.GetPrimAtPath.return_value = mock_prim

        mock_stage.GetRootLayer.return_value = mock_layer
        mock_layer.subLayerPaths = ["./look/look.usda", "./model/model.usda"]

        with patch(f"{MODULE_PATH}.Usd.ModelAPI") as mock_model_api_class:
            mock_model_api_instance = MagicMock()
            mock_model_api_instance.GetKind.return_value = Kind.Tokens.component
            mock_model_api_class.return_value = mock_model_api_instance

            mock_stage_open.return_value = mock_stage

            # Act
            result = self.validator.validate_asset(self.root_dir, self.asset_name)

            # Assert
            self.assertTrue(result)
            self.assertEqual(len(self.validator._errors), 0)

    @patch.object(Path, "exists")
    def test_validate_stage_missing_file_appends_error(
        self, mock_exists: MagicMock
    ) -> None:
        # Arrange
        mock_exists.return_value = False
        target_path = self.root_dir / "model" / "model.usda"

        # Act
        self.validator._validate_stage(target_path, "/prop_mesa", "model", "geo")

        # Assert
        self.assertIn("File for 'model' does not exist", self.validator._errors)
        self.assertEqual(len(self.validator._errors), 1)

    @patch_usd_open()
    @patch.object(Path, "exists")
    def test_validate_stage_missing_root_prim(
        self, mock_exists: MagicMock, mock_stage_open: MagicMock
    ) -> None:
        # Arrange
        mock_exists.return_value = True
        mock_stage = MagicMock(spec=Usd.Stage)
        mock_stage.GetPrimAtPath.return_value = None
        mock_stage_open.return_value = mock_stage

        # Act
        self.validator._validate_stage(Path("dummy.usda"), "/prop_mesa", "model", "geo")

        # Assert
        self.assertIn(
            "'model' file does not contain required root prim: '/prop_mesa'",
            self.validator._errors,
        )

    @patch_usd_open()
    @patch.object(Path, "exists")
    def test_validate_stage_missing_scope_container(
        self, mock_exists: MagicMock, mock_stage_open: MagicMock
    ) -> None:
        # Arrange
        mock_exists.return_value = True
        mock_stage = MagicMock(spec=Usd.Stage)
        mock_stage.GetPrimAtPath.side_effect = lambda path: path == "/prop_mesa"
        mock_stage_open.return_value = mock_stage

        # Act
        self.validator._validate_stage(Path("dummy.usda"), "/prop_mesa", "model", "geo")

        # Assert
        self.assertIn(
            "'model' file does not contain required scope cointainer: 'geo'",
            self.validator._errors,
        )

    @patch_usd_open()
    @patch.object(Path, "exists")
    def test_validate_payload_missing_sublayer_registration(
        self, mock_exists: MagicMock, mock_stage_open: MagicMock
    ) -> None:
        # Arrange
        mock_exists.return_value = True
        mock_stage = MagicMock(spec=Usd.Stage)
        mock_layer = MagicMock(spec=Sdf.Layer)
        mock_layer.subLayerPaths = []
        mock_stage.GetRootLayer.return_value = mock_layer
        mock_stage_open.return_value = mock_stage

        # Act
        self.validator._validate_payload(
            Path("payload.usda"), self.mock_departments_data
        )

        # Assert
        self.assertIn(
            "Expected sublayers './model/model.usda' not found", self.validator._errors
        )
        self.assertIn(
            "Expected sublayers './look/look.usda' not found", self.validator._errors
        )

    @patch_usd_open()
    @patch.object(Path, "exists")
    def test_validate_root_invalid_kind_metadata(
        self, mock_exists: MagicMock, mock_stage_open: MagicMock
    ) -> None:
        # Arrange
        mock_exists.return_value = True
        mock_stage = MagicMock(spec=Usd.Stage)
        mock_prim = MagicMock(spec=Usd.Prim)

        mock_stage.GetPrimAtPath.return_value = mock_prim
        mock_stage_open.return_value = mock_stage

        with patch(f"{MODULE_PATH}.Usd.ModelAPI") as mock_model_api_class:
            mock_model_api_instance = MagicMock()
            mock_model_api_instance.GetKind.return_value = "assembly"
            mock_model_api_class.return_value = mock_model_api_instance

            # Act
            self.validator._validate_root(
                Path("root.usda"), "/prop_mesa", "payload.usda"
            )

            # Assert
            self.assertIn(
                "Invalid 'kind' metadata. Expected type: 'component', found: 'assembly'",
                self.validator._errors,
            )
