"""Integration coverage for the two migrated content pages."""
from test_qml_dashboard import shell
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QColor
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtTest import QTest


def item(quick, name):
    pending = [quick.rootObject()]
    while pending:
        candidate = pending.pop()
        if candidate.objectName() == name:
            return candidate
        pending.extend(candidate.childItems())
    raise AssertionError(name)


def test_pages_render_resize_and_select(shell):
    w = shell
    for index, quick in w.qml_pages.items():
        assert quick.status() == QQuickWidget.Ready, w.qml_page_errors
        assert w.qml_page_hosts[index].currentWidget() is quick
    w.navigation.setCurrentRow(1)
    quick = w.qml_pages[1]
    for width, columns in ((720, 2), (1100, 3)):
        w.resize(width, 780)
        QTest.qWait(30)
        assert item(quick, 'characterGallery').property('columns') == columns
        assert w.pages.currentWidget().horizontalScrollBar().maximum() == 0
    button = item(quick, 'select_miles_morales')
    QTest.mouseClick(quick, Qt.LeftButton, pos=button.mapToScene(button.boundingRect().center()).toPoint())
    assert w.character_mgr.active_character.id == 'miles_morales'


def test_search_settings_and_live_home(shell, qapp):
    w = shell
    w.search_input.setText('opacity')
    w._open_first_search_result()
    qapp.processEvents()
    assert w.qml_pages[1].rootObject().property('revealedSetting') == 'general.opacity'
    assert w.qml_bridge.setCharacterOpacity(75)
    assert item(w.qml_pages[1], 'characterOpacity').property('value') == 75
    assert not w.qml_bridge.setCharacterSize(float('nan'))
    w.navigation.setCurrentRow(0)
    frame = QPixmap(32, 32)
    frame.fill(QColor('red'))
    before = w.qml_bridge.frameRevision
    w.update_preview(frame)
    assert w.qml_bridge.frameRevision > before
    assert w.qml_frame_provider.frame.pixelColor(0, 0) == QColor('red')
    w.update_companion_stats({'distance_text':'12 m', 'webs_text':'4', 'active_text':'2 min'})
    qapp.processEvents()
    assert w.qml_bridge.homeData['focus'] == '2 min'
    requested = []
    w.focus_timer_started.connect(requested.append)
    w.qml_bridge.homeAction('focus25')
    assert requested == [25]
    assert w.settings.get('behavior.focus_mode')


def test_page_error_uses_native_fallback(shell):
    from PySide6.QtCore import QUrl
    quick = shell.qml_pages[1]
    quick.setSource(QUrl.fromLocalFile('G:/missing-dashboard-page.qml'))
    assert quick.status() == QQuickWidget.Error
    assert shell.qml_page_hosts[1].currentWidget() is not quick


def test_import_keeps_existing_dialog_flow(shell, monkeypatch):
    opened = []
    class Dialog:
        def __init__(self, manager, parent):
            opened.append(manager)
        def exec(self):
            return 0
    monkeypatch.setattr('ui.character_selection.AddCharacterDialog', Dialog)
    shell.qml_bridge.importCharacter()
    assert opened == [shell.character_mgr]
