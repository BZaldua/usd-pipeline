import unittest
from unittest.mock import MagicMock, patch

from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QInputDialog

from src.config import ConfigManager
from src.ui import MainWindow, QtSignalingHandler

app_qt = QApplication.instance() or QApplication([])


class TestMainWindow(unittest.TestCase):

    def setUp(self):
        self.mock_config = MagicMock(spec=ConfigManager)
        self.mock_handler = QtSignalingHandler()
        self.mock_config.setup_logging.return_value = self.mock_handler

        self.window = MainWindow()

        self.original_get_existing_directory = MainWindow.browse_dir
        self.original_get_text = QInputDialog.getText
        self.root_dir = "/pipeline/projects/test_asset"

    def tearDown(self):
        self.window.close()
        QInputDialog.getText = self.original_get_text

    def test_init_state_buttons_are_disabled(self):
        # Assert
        self.assertFalse(self.window.create_btn.isEnabled())
        self.assertFalse(self.window.validate_btn.isEnabled())

    @patch("PyQt6.QtWidgets.QFileDialog.getExistingDirectory")
    def test_browse_dir_updates_ui_and_enables_buttons(self, mock_get_dir):
        # Arrange
        mock_path = self.root_dir
        mock_get_dir.return_value = mock_path

        QTest.mouseClick(
            self.window.centralWidget().findChild(type(self.window.create_btn)),
            Qt.MouseButton.LeftButton,
        )

        # Act
        self.window.browse_dir()

        # Assert
        self.assertEqual(self.window.root_dir, mock_path)
        self.assertEqual(self.window.route_txt.text(), mock_path)
        self.assertTrue(self.window.create_btn.isEnabled())
        self.assertTrue(self.window.validate_btn.isEnabled())

    @patch("src.ui.main_window.ProjectBootstrap")
    def test_create_asset_success_triggers_bootstrap(self, mock_bootstrap_class):
        # Arrange
        self.window.root_dir = self.root_dir
        self.window.create_btn.setEnabled(True)

        QInputDialog.getText = MagicMock(return_value=("character_concept", True))

        # Act
        QTest.mouseClick(self.window.create_btn, Qt.MouseButton.LeftButton)

        # Assert
        mock_bootstrap_class.assert_called_once_with(
            self.window.root_dir, self.window.config
        )
        mock_bootstrap_class.return_value.run.assert_called_once_with(
            "character_concept"
        )

    @patch("src.ui.main_window.ProjectBootstrap")
    def test_create_asset_empty_name_does_not_trigger_bootstrap(
        self, mock_bootstrap_class
    ):
        # Arrange
        self.window.root_dir = self.root_dir
        self.window.create_btn.setEnabled(True)

        QInputDialog.getText = MagicMock(return_value=("   ", True))

        # Act
        QTest.mouseClick(self.window.create_btn, Qt.MouseButton.LeftButton)

        # Assert
        mock_bootstrap_class.assert_not_called()

    @patch("src.ui.main_window.UsdValidator")
    def test_validate_asset_triggers_validator(self, mock_validator_class):
        # Arrange
        self.window.root_dir = self.root_dir
        self.window.validate_btn.setEnabled(True)

        # Act
        QTest.mouseClick(self.window.validate_btn, Qt.MouseButton.LeftButton)

        # Assert
        mock_validator_class.asset_called_once_with(self.window.root_dir)

    def test_write_console_appends_text_to_ui(self):
        # Arrange
        log_message = "[INFO] Asset structure loaded successfully."

        # Act
        self.window.write_console(log_message)

        # Assert
        self.assertIn(log_message, self.window.logs_txt.toPlainText())
