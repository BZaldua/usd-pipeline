import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
import tempfile
import shutil

from src.core import UsdValidator

class TestUsdValidator(unittest.TestCase):

    def setUp(self):
        self.mock_config = MagicMock()
        self.mock_config.get.return_value = {
            "model": {"dir_name": "model_dir", "scope_name": "geo", "format": "usd"},
            "shading": {"dir_name": "shading_dir", "scope_name": "mtl", "format": "usd"}
        }
        self.validator = UsdValidator(self.mock_config)
        self.test_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_find_latest_department_version_success(self):
        # Arrange
        mock_dir = MagicMock(spec=Path)
        mock_dir.exists.return_value = True

        file1 = MagicMock(spec=Path)
        file1.is_dir.return_value = False
        file1.name = "assetA_model_v001.usd"

        file2 = MagicMock(spec=Path)
        file2.is_dir.return_value = False
        file2.name = "assetA_model_v002.usd"

        mock_dir.iterdir.return_value = [file1, file2]

        # Act
        result = self.validator._find_latest_department_version(mock_dir, "assetA", "model")

        # Assert
        self.assertEqual(result, file2)
        self.assertEqual(len(self.validator._warnings), 0)

    def test_find_latest_department_version_unsupported_name(self):
        # Arrange
        mock_dir = MagicMock(spec=Path)
        mock_dir.exists.return_value = True

        invalid_file = MagicMock(spec=Path)
        invalid_file.is_dir.return_value = False
        invalid_file.name = "invalid_file_name.usd"

        mock_dir.iterdir.return_value = [invalid_file]

        # Act
        result = self.validator._find_latest_department_version(mock_dir, "assetA", "model")

        # Assert
        self.assertIsNone(result)
        self.assertEqual(len(self.validator._warnings), 1)
        self.assertIn("unsupported name/format", self.validator._warnings[0])

    @patch('pxr.Sdf.Layer.FindOrOpen')
    def test_validate_department_layer_missing_root_prim(self, mock_find_or_open):
        # Arrange
        mock_layer = MagicMock()
        mock_find_or_open.return_value = mock_layer
        mock_layer.GetPrimAtPath.return_value = None

        # Act
        self.validator._validate_department_layer(Path("/fake/path.usd"), "/assetA", "model", "geo")

        # Assert
        self.assertTrue(any("Required root prim is missing" in err for err in self.validator._errors))

    @patch('pxr.Sdf.Layer.FindOrOpen')
    def test_validate_model_structure_forbidden_element(self, mock_find_or_open):
        # Arrange
        mock_layer = MagicMock()
        mock_find_or_open.return_value = mock_layer

        mock_root_spec = MagicMock()
        mock_root_spec.typeName = "Xform"
        
        mock_child_spec = MagicMock()
        mock_child_spec.typeName = "Material"
        mock_child_spec.path = "/assetA/Material"
        mock_child_spec.nameChildren = []

        mock_root_spec.nameChildren = [mock_child_spec]
        mock_layer.GetPrimAtPath.return_value = mock_root_spec

        # Act
        self.validator._validate_model_structure(Path("/fake/model.usd"), "/assetA")

        # Assert
        self.assertTrue(any("Forbidden element 'Material'" in err for err in self.validator._errors))

    @patch('pxr.Sdf.Layer.FindOrOpen')
    def test_validate_model_structure_mesh_no_vertices(self, mock_find_or_open):
        # Arrange
        mock_layer = MagicMock()
        mock_find_or_open.return_value = mock_layer

        mock_root_spec = MagicMock()
        mock_root_spec.typeName = "Xform"

        mock_mesh_spec = MagicMock()
        mock_mesh_spec.typeName = "Mesh"
        mock_mesh_spec.path = "/assetA/geo/mesh"
        
        mock_points = MagicMock()
        mock_points.default = []
        mock_mesh_spec.attributes = {"points": mock_points}
        mock_mesh_spec.nameChildren = []

        mock_root_spec.nameChildren = [mock_mesh_spec]
        mock_layer.GetPrimAtPath.return_value = mock_root_spec

        # Act
        self.validator._validate_model_structure(Path("/fake/model.usd"), "/assetA")

        # Assert
        self.assertTrue(any("Geo mesh with no vertices" in err for err in self.validator._errors))

    @patch('pxr.Sdf.Layer.FindOrOpen')
    def test_validate_payload_missing_sublayer(self, mock_find_or_open):
        # Arrange
        mock_file_path = MagicMock(spec=Path)
        mock_file_path.exists.return_value = True
        mock_file_path.name = "assetA_payload.usda"

        mock_layer = MagicMock()
        mock_layer.subLayerPaths = ["./layers/shading_dir/assetA_shading_v001.usd"]
        mock_find_or_open.return_value = mock_layer

        departments = {
            "model": {"dir_name": "model_dir"},
            "shading": {"dir_name": "shading_dir"}
        }
        resolved_files = {
            "model": Path("/root/layers/model_dir/assetA_model_v001.usd"),
            "shading": Path("/root/layers/shading_dir/assetA_shading_v001.usd")
        }

        # Act
        self.validator._validate_payload(mock_file_path, departments, resolved_files)

        # Assert
        self.assertTrue(any("[Payload] The assembly file is not calling correct version of model" in err for err in self.validator._errors))

    @patch('pxr.Kind.Tokens')
    @patch('pxr.Sdf.Layer.FindOrOpen')
    def test_validate_root_invalid_kind(self, mock_find_or_open, mock_tokens):
        # Arrange
        mock_file_path = MagicMock(spec=Path)
        mock_file_path.exists.return_value = True

        mock_layer = MagicMock()
        mock_prim_spec = MagicMock()
        mock_tokens.component = "component"
        mock_prim_spec.kind = "subcomponent"
        
        mock_layer.GetPrimAtPath.return_value = mock_prim_spec
        mock_find_or_open.return_value = mock_layer

        # Act
        self.validator._validate_root(mock_file_path, "/assetA")

        # Assert
        self.assertTrue(any("missing or invalid 'kind'" in err for err in self.validator._errors))

    @patch('pxr.UsdGeom.PrimvarsAPI')
    @patch('pxr.Usd.Stage.Open')
    def test_validate_stage_content_missing_uvs_warning(self, mock_stage_open, mock_primvars_api_cls):
        # Arrange
        mock_stage = MagicMock()
        mock_stage_open.return_value = mock_stage

        mock_prim = MagicMock()
        mock_prim.IsA.return_value = True 
        mock_stage.Traverse.return_value = [mock_prim]

        mock_primvars_api = MagicMock()
        mock_primvars_api.HasPrimvar.return_value = False
        mock_primvars_api_cls.return_value = mock_primvars_api

        with self.assertLogs('src', level='WARNING') as log_capture:
            # Act
            self.validator._validate_stage_content(Path("/fake/root.usda"))

            # Assert
            self.assertTrue(any("does not contain texture coordinates" in msg for msg in log_capture.output))

    @patch.object(UsdValidator, '_validate_stage_content')
    @patch.object(UsdValidator, '_validate_root')
    @patch.object(UsdValidator, '_validate_payload')
    @patch.object(UsdValidator, '_validate_model_structure')
    @patch.object(UsdValidator, '_validate_department_layer')
    @patch.object(UsdValidator, '_find_latest_department_version')
    def test_validate_asset_integration_success(
        self, mock_find_version, mock_val_dept, mock_val_model, mock_val_payload, mock_val_root, mock_val_stage
    ):
        # Arrange
        mock_find_version.side_effect = [
            Path("assetA_model_v001.usd"),
            Path("assetA_shading_v001.usd")
        ]

        with patch.object(Path, 'exists', return_value=True):
            # Act
            result = self.validator.validate_asset(self.test_dir, "assetA")

        # Assert
        self.assertTrue(result)
        self.assertEqual(len(self.validator._errors), 0)