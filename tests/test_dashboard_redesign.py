"""Verify live feature ownership and settings search, not mockup markup."""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase
from core.character_manager import CharacterManager
from services.settings_service import SettingsService
from ui.main_window import MainWindow
from ui.dashboard_design import DESTINATIONS


@pytest.fixture
def dashboard(qapp, tmp_path, monkeypatch):
    settings = SettingsService(config_dir=tmp_path)
    monkeypatch.setattr('ui.main_window.get_settings', lambda: settings)
    manager = CharacterManager()
    manager.set_active_character('tom_holland')
    QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf')
    window = MainWindow(manager)
    window.show()
    yield window
    window.hide()
    window.deleteLater()
    qapp.processEvents()


def belongs(window, widget, page):
    return window.pages.widget(page).isAncestorOf(widget)


def test_feature_owners_and_real_bindings(dashboard):
    w = dashboard
    assert [w.navigation.item(i).text() for i in range(w.navigation.count())] == [d[0] for d in DESTINATIONS]
    assert belongs(w, w.size_slider, 1)
    assert belongs(w, w.chk_simulate_music, 2)
    assert belongs(w, w.title_offset_slider, 3)
    assert belongs(w, w.focus_mode_chk, 4)
    assert belongs(w, w._activity_checkboxes['focus_read'], 4)
    assert belongs(w, w.spin_eye_break_mins, 4)
    assert belongs(w, w.chk_master_hotkeys, 5)
    assert belongs(w, w._bindings['system.click_through'][0], 5)
    assert belongs(w, w._bindings['general.display_fps'][0], 6)
    w.size_slider.setValue(180)
    assert w.settings.get('general.scale') == .9
    w.settings.set('general.scale', 1.25)
    assert w.size_slider.value() == 250


def test_search_opens_music_category_without_changing_setting(dashboard, qapp):
    w = dashboard
    before = w.settings.get('behavior.enable_audio_beat_bobbing')
    w.search_input.setText('headphones')
    assert w.search_results.count() > 0
    assert w.search_results.item(0).data(Qt.UserRole) is not None
    w._open_first_search_result()
    qapp.processEvents()
    assert w.pages.currentIndex() == 2
    assert w.activity_tabs.tabText(w.activity_tabs.currentIndex()) == 'Music & Sound'
    assert w.settings.get('behavior.enable_audio_beat_bobbing') == before
    assert not w.search_results.isVisible()


@pytest.mark.parametrize('width,height', [(720,600),(1100,780)])
def test_all_pages_fit_and_preview_appears(dashboard, qapp, width, height):
    w = dashboard
    w.resize(width,height)
    for index in range(7):
        w.navigation.setCurrentRow(index)
        for _ in range(5):
            qapp.processEvents()
        assert w.pages.currentWidget().horizontalScrollBar().maximum() == 0, index
    assert w.preview.pixmap() and not w.preview.pixmap().isNull()
