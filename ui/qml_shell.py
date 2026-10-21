"""Embed the QML shell while preserving existing native pages during migration."""
import logging
from pathlib import Path
from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QStackedWidget
from PySide6.QtQuickWidgets import QQuickWidget
from .qml_bridge import DashboardBridge

logger = logging.getLogger('SpiderBuddy.QmlShell')


def install_qml_shell(window, source=None):
    native = window.sidebar
    host = QStackedWidget(window)
    host.setObjectName('navigationHost')
    host.setFixedWidth(native.width())
    window.main_root_layout.replaceWidget(native, host)
    native.setMinimumWidth(0)
    native.setMaximumWidth(16777215)
    host.addWidget(native)
    window.sidebar = host
    window.native_sidebar = native

    quick = QQuickWidget(host)
    quick.setObjectName('qmlNavigation')
    quick.setResizeMode(QQuickWidget.SizeRootObjectToView)
    quick.setClearColor(QColor(Qt.transparent))
    quick.setFocusPolicy(Qt.StrongFocus)
    host.addWidget(quick)
    bridge = DashboardBridge(window.settings, window.character_mgr, quick)
    bridge.navigateRequested.connect(window.navigation.setCurrentRow)
    window.navigation.currentRowChanged.connect(bridge.sync_route)
    bridge.characterRequested.connect(window.character_changed.emit)
    bridge.activityToggleRequested.connect(window._on_activity_toggled)
    bridge.pauseRequested.connect(window._toggle_running_state)
    bridge.searchRequested.connect(window.search_input.setFocus)
    bridge.sync_route(max(0, window.navigation.currentRow()))
    bridge.set_status(window._is_running, window._status_text)
    window.qml_bridge = bridge
    window.qml_sidebar = quick
    window.qml_errors = []

    def status_changed(status):
        if status == QQuickWidget.Ready:
            host.setCurrentWidget(quick)
        elif status == QQuickWidget.Error:
            window.qml_errors = [error.toString() for error in quick.errors()]
            logger.error('QML navigation unavailable; using native navigation: %s', window.qml_errors)
            host.setCurrentWidget(native)

    quick.statusChanged.connect(status_changed)
    quick.rootContext().setContextProperty('dashboardBridge', bridge)
    path = Path(source) if source else Path(__file__).parent / 'qml' / 'Sidebar.qml'
    quick.setSource(QUrl.fromLocalFile(str(path.resolve())))
    status_changed(quick.status())
    return quick
