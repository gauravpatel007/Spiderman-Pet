"""QML page hosts sharing the existing application controller."""
import logging
from pathlib import Path
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor, QImage
from PySide6.QtQuick import QQuickImageProvider
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtWidgets import QStackedWidget, QSizePolicy


class CompanionFrames(QQuickImageProvider):
    def __init__(self, pixmap):
        super().__init__(QQuickImageProvider.Image)
        self.frame = pixmap.toImage() if pixmap is not None else QImage()

    def requestImage(self, image_id, size, requested_size):
        size.setWidth(self.frame.width())
        size.setHeight(self.frame.height())
        return self.frame


class ActivityImageProvider(QQuickImageProvider):
    def __init__(self, library):
        super().__init__(QQuickImageProvider.Image)
        self.library = library
        self.frame = QImage()

    def requestImage(self, image_id, size, requested_size):
        clean_id = image_id.split('?')[0]
        if clean_id.startswith('thumb/'):
            name = clean_id[6:]
            img = self.library.get_thumbnail(name)
            if img is not None and not img.isNull():
                size.setWidth(img.width())
                size.setHeight(img.height())
                return img
        size.setWidth(self.frame.width())
        size.setHeight(self.frame.height())
        return self.frame


def install_qml_pages(window):
    bridge = window.qml_bridge
    bridge.home_source = window
    bridge.importRequested.connect(window.char_selection_widget._open_add_dialog)

    def action(name):
        if name == 'quote':
            window._cycle_spidey_quote()
        elif name in ('chill', 'hyper', 'camo'):
            window._set_mood_preset(name)
        elif name == 'focus25':
            window._start_pomodoro_focus(25)
        elif name == 'break5':
            window._start_pomodoro_break(5)
        elif name == 'resetTimer':
            window._reset_pomodoro()
        else:
            window._trigger_quick_action(name)
    bridge.homeActionRequested.connect(action)
    from .activity_library import ActivityLibrary
    window.activity_library = ActivityLibrary(window)
    window.qml_pages = {}
    window.qml_page_hosts = {}
    window.qml_page_errors = {}
    for index, filename in ((0, 'HomePage.qml'), (1, 'CharactersPage.qml'), (2, 'ActivitiesPage.qml')):
        scroll = window.pages.widget(index)
        native = scroll.takeWidget()
        host = QStackedWidget()
        host.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        host.addWidget(native)
        quick = QQuickWidget(host)
        quick.setResizeMode(QQuickWidget.SizeRootObjectToView)
        is_dark = bridge.darkTheme if (bridge and hasattr(bridge, 'darkTheme')) else True
        quick.setClearColor(QColor('#080B14' if is_dark else '#F2F4F8'))
        quick.setFocusPolicy(Qt.StrongFocus)
        host.addWidget(quick)
        scroll.setWidget(host)
        window.qml_pages[index] = quick
        window.qml_page_hosts[index] = host
        quick.rootContext().setContextProperty('dashboardBridge', bridge)
        if index == 2:
            quick.rootContext().setContextProperty('activityLibrary', window.activity_library)
            provider = ActivityImageProvider(window.activity_library)
            window.activity_library.provider = provider
            quick.engine().addImageProvider('activity', provider)
        if index == 0:
            provider = CompanionFrames(getattr(window, '_last_preview', None))
            window.qml_frame_provider = provider
            quick.engine().addImageProvider('companion', provider)

        def status_changed(status, quick=quick, host=host, native=native, index=index):
            if status == QQuickWidget.Ready:
                host.setCurrentWidget(quick)
            elif status == QQuickWidget.Error:
                errors = [error.toString() for error in quick.errors()]
                window.qml_page_errors[index] = errors
                logging.getLogger('SpiderBuddy.QmlPages').error('%s', errors)
                host.setCurrentWidget(native)
        quick.statusChanged.connect(status_changed)
        quick.setSource(QUrl.fromLocalFile(str(Path(__file__).parent / 'qml' / filename)))
        status_changed(quick.status())
    bridge.refresh_home()
