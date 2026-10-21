"""Exercise the actual QML shell and its shared Python state."""
import os
os.environ.setdefault('QT_QUICK_BACKEND', 'software')

import pytest
from PySide6.QtCore import QObject, Qt, QUrl
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtTest import QTest
from core.character_manager import CharacterManager
from services.settings_service import SettingsService
from ui.main_window import MainWindow


@pytest.fixture
def shell(qapp, tmp_path, monkeypatch):
    settings = SettingsService(config_dir=tmp_path)
    monkeypatch.setattr('ui.main_window.get_settings', lambda: settings)
    manager = CharacterManager()
    manager.set_active_character('tom_holland')
    window = MainWindow(manager)
    window.character_changed.connect(manager.set_active_character)
    window.stop_requested.connect(lambda: window.set_running(False))
    window.start_requested.connect(lambda: window.set_running(True))
    window.show()
    QTest.qWait(60)
    yield window
    window.hide()
    window.deleteLater()
    qapp.processEvents()


def click_item(window, name):
    root = window.qml_sidebar.rootObject()
    # Repeater delegates belong to the visual tree, not necessarily QObject's tree.
    pending = [root]
    item = None
    while pending:
        candidate = pending.pop()
        if candidate.objectName() == name:
            item = candidate
            break
        pending.extend(candidate.childItems())
    assert item is not None, name
    # The sidebar scrolls on smaller displays; native clicks must target a
    # visible delegate rather than coordinates outside the viewport.
    ancestor = item.parentItem()
    while ancestor is not None:
        if ancestor.metaObject().indexOfProperty('contentY') >= 0:
            local = item.mapToItem(ancestor, item.boundingRect().center())
            if local.y() < 0 or local.y() >= ancestor.height():
                ancestor.setProperty('contentY', max(0, min(
                    ancestor.property('contentHeight') - ancestor.height(),
                    ancestor.property('contentY') + local.y() - ancestor.height() / 2)))
                QTest.qWait(20)
        ancestor = ancestor.parentItem()
    center = item.mapToScene(item.boundingRect().center()).toPoint()
    QTest.mouseClick(window.qml_sidebar, Qt.LeftButton, pos=center)
    QTest.qWait(20)
    return item


def test_qml_load_click_navigation_and_search_sync(shell, qapp):
    w = shell
    assert w.qml_sidebar.status() == QQuickWidget.Ready, w.qml_errors
    assert w.sidebar.currentWidget() is w.qml_sidebar
    click_item(w, 'route_4')
    assert w.pages.currentIndex() == w.qml_bridge.currentRoute == 4
    w.navigation.setCurrentRow(2)
    assert w.qml_bridge.currentRoute == 2
    w.search_input.setText('opacity')
    w._open_first_search_result()
    qapp.processEvents()
    assert w.qml_bridge.currentRoute == w.pages.currentIndex() == 1
    w.qml_bridge.navigate(99)
    assert w.pages.currentIndex() == 1


def test_qml_focus_and_theme_persist_and_observe_external_changes(shell, qapp):
    w = shell
    switch = click_item(w, 'focusSwitch')
    assert w.settings.get('behavior.focus_mode') is True
    assert w.focus_mode_chk.isChecked()
    w.settings.set('behavior.focus_mode', False)
    qapp.processEvents()
    assert not switch.property('checked')
    assert w.qml_bridge.setTheme('light')
    assert not w.qml_bridge.darkTheme
    assert not w.qml_bridge.setTheme('unknown')
    reloaded = SettingsService(config_dir=w.settings.user_dir)
    assert reloaded.get('general.theme') == 'light'
    w.settings.set('general.theme', 'dark')
    assert w.qml_bridge.darkTheme


def test_shared_character_activity_and_status_models(shell):
    w = shell
    bridge = w.qml_bridge
    assert bridge.selectCharacter('miles_morales')
    assert w.character_mgr.active_character.id == 'miles_morales'
    assert [row['id'] for row in bridge.characters if row['selected']] == ['miles_morales']
    assert not bridge.selectCharacter('missing')
    assert bridge.setActivityEnabled('dance', False)
    assert not w._activity_checkboxes['dance'].isChecked()
    assert not next(row for row in bridge.activities if row['id'] == 'dance')['enabled']
    assert not bridge.setActivityEnabled('not_an_activity', True)
    snapshot = bridge.settingsValues
    snapshot['general']['theme'] = 'invalid'
    assert w.settings.get('general.theme') != 'invalid'
    bridge.togglePause()
    assert not bridge.running and bridge.activity == 'Paused'
    bridge.togglePause()
    assert bridge.running
    w.update_battery_status(72, True, False)
    assert bridge.battery == '72% · Charging'


def test_qml_failure_falls_back_to_native_navigation(shell, tmp_path, qapp):
    w = shell
    w.qml_sidebar.setSource(QUrl.fromLocalFile(str(tmp_path/'missing.qml')))
    qapp.processEvents()
    assert w.qml_sidebar.status() == QQuickWidget.Error
    assert w.sidebar.currentWidget() is w.native_sidebar
    assert w.qml_errors
    w.navigation.setCurrentRow(6)
    assert w.pages.currentIndex() == 6
