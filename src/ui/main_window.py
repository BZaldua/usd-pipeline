import logging
from pathlib import Path

from PyQt6.QtCore import QDir, QObject, pyqtSignal
from PyQt6.QtGui import QFileSystemModel, QTextCursor
from PyQt6.QtWidgets import (QFileDialog, QHBoxLayout, QHeaderView,
                             QInputDialog, QLabel, QLineEdit, QMainWindow,
                             QPushButton, QTextEdit, QTreeView, QVBoxLayout,
                             QWidget)

from src.config import ConfigManager
from src.core import ProjectBootstrap, UsdValidator

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pipeline - Bootstrap & Validator")
        self.resize(800, 500)

        self.root_dir = ""
        self.model = QFileSystemModel()
        self.model.setFilter(QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot)

        self.config = ConfigManager()
        self.validator = UsdValidator(self.config)

        self.setup_logging()
        self.init_ui()

    def setup_logging(self):
        self.qt_handler = self.config.setup_logging(QtSignalingHandler)
        if self.qt_handler:
            self.qt_handler.log_signal.connect(self.write_console)

    def write_console(self, log):
        self.logs_txt.append(log)
        self.logs_txt.moveCursor(QTextCursor.MoveOperation.End)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        # --- TOP: ROOT DIR SELECTOR ---
        top_layout = QHBoxLayout()

        route_label = QLabel("Root dir:")

        self.route_txt = QLineEdit()
        self.route_txt.setReadOnly(True)
        self.route_txt.setPlaceholderText("Select root dir...")

        search_btn = QPushButton("Browse...")
        search_btn.clicked.connect(self.browse_dir)

        top_layout.addWidget(route_label)
        top_layout.addWidget(self.route_txt)
        top_layout.addWidget(search_btn)

        main_layout.addLayout(top_layout)

        # -- MIDDLE-TOP: ACTION BUTTONS
        action_btn_layout = QHBoxLayout()
        action_btn_layout.addStretch()

        self.create_btn = QPushButton("Create asset")
        self.create_btn.setEnabled(False)
        self.create_btn.setMaximumWidth(100)
        self.create_btn.clicked.connect(self.create_asset)

        self.validate_btn = QPushButton("Validate")
        self.validate_btn.setEnabled(False)
        self.validate_btn.setMaximumWidth(100)
        self.validate_btn.clicked.connect(self.validate)

        action_btn_layout.addWidget(self.create_btn)
        action_btn_layout.addWidget(self.validate_btn)

        main_layout.addLayout(action_btn_layout)

        # -- MIDDLE: DIR TREE --
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.model)

        self.tree_view.setColumnHidden(1, False)
        self.tree_view.setColumnHidden(2, True)
        self.tree_view.setColumnHidden(3, True)

        tree_view_header = self.tree_view.header()
        tree_view_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        tree_view_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.tree_view.setColumnWidth(1, 120)

        main_layout.addWidget(self.tree_view)

        # -- BOTTOM: CONSOLE --
        console_lbl = QLabel("Console")

        self.logs_txt = QTextEdit()
        self.logs_txt.setReadOnly(True)
        self.logs_txt.setMaximumHeight(120)

        main_layout.addWidget(console_lbl)
        main_layout.addWidget(self.logs_txt)

    def browse_dir(self):
        dir = QFileDialog.getExistingDirectory(self, "Select root directory")
        if dir:
            self.root_dir = dir
            self.route_txt.setText(dir)
            self.model.setRootPath(dir)
            self.tree_view.setRootIndex(self.model.index(dir))
            self.create_btn.setEnabled(True)
            self.validate_btn.setEnabled(True)

    def create_asset(self):
        if not self.root_dir:
            return

        asset_name, ok = QInputDialog.getText(
            self, "New asset", "Insert name of the asset to create"
        )
        if ok and asset_name.strip():
            root_dir_path = self.root_dir
            bootstrap = ProjectBootstrap(root_dir_path, self.config)
            bootstrap.run(asset_name.strip())

    def validate(self):
        if not self.root_dir:
            return

        root_dir_path = Path(self.root_dir).resolve()
        self.validator.validate_dir_assets(root_dir_path)


class QtSignalingHandler(logging.Handler, QObject):
    log_signal = pyqtSignal(str)

    def __init__(self):
        logging.Handler.__init__(self)
        QObject.__init__(self)

    def emit(self, record):
        msg = self.format(record)
        self.log_signal.emit(msg)
