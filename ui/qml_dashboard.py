"""QML Dashboard controller and window manager."""
import logging
import os
import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QUrl, Qt
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication

# Ensure project root is in sys.path even when executed directly from ui/ directory
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from ui.bridge.settings_bridge import SettingsBridge
from ui.bridge.character_model import CharacterModel
from ui.bridge.activity_model import ActivityModel
from ui.bridge.status_model import StatusModel

logger = logging.getLogger("SpiderBuddy.UI.QmlDashboard")


class QmlDashboard(QObject):
    """Manages the lifecycle, bridge models, and display of the Qt Quick / QML dashboard."""

    def __init__(self, character_mgr=None, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.character_mgr = character_mgr
        self.engine = QQmlApplicationEngine()

        # Initialize Bridge Models
        self.settings_bridge = SettingsBridge(parent=self)
        self.character_model = CharacterModel(character_manager=self.character_mgr, parent=self)
        self.activity_model = ActivityModel(parent=self)
        self.status_model = StatusModel(parent=self)

        # Register context properties into QML
        ctx = self.engine.rootContext()
        ctx.setContextProperty("settingsBridge", self.settings_bridge)
        ctx.setContextProperty("characterModel", self.character_model)
        ctx.setContextProperty("activityModel", self.activity_model)
        ctx.setContextProperty("statusModel", self.status_model)

        # Load AppShell.qml
        qml_path = Path(__file__).parent / "qml" / "AppShell.qml"
        if not qml_path.exists():
            raise FileNotFoundError(f"AppShell.qml not found at {qml_path}")

        # Connect exit on load failure
        self.engine.load(QUrl.fromLocalFile(str(qml_path)))
        self._root_objects = self.engine.rootObjects()
        if not self._root_objects:
            raise RuntimeError(f"Failed to load QML from {qml_path}")
        self.window = self._root_objects[0]

    def show(self):
        """Display the dashboard window and bring to front."""
        if self.window:
            self.window.show()
            self.window.raise_()
            self.window.requestActivate()

    def hide(self):
        """Hide dashboard."""
        if self.window:
            self.window.hide()

    def is_visible(self) -> bool:
        """Check if dashboard window is currently visible."""
        return bool(self.window and self.window.isVisible())

    def close(self):
        """Close dashboard window."""
        if self.window:
            self.window.close()


def launch_standalone():
    """Standalone launcher for testing and previewing the QML dashboard."""
    logging.basicConfig(level=logging.INFO)
    app = QApplication.instance()
    owns_app = False
    if app is None:
        app = QApplication(sys.argv)
        owns_app = True

    dashboard = QmlDashboard()
    dashboard.show()

    if owns_app:
        sys.exit(app.exec())
    return dashboard


if __name__ == "__main__":
    launch_standalone()
