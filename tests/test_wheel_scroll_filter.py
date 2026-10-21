"""Test verifying WheelScrollIgnoreFilter prevents accidental wheel value changes across all input widgets."""
import pytest
from PySide6.QtWidgets import QApplication, QSlider, QSpinBox, QComboBox, QScrollArea, QWidget, QVBoxLayout
from PySide6.QtCore import Qt, QEvent, QPointF, QPoint
from PySide6.QtGui import QWheelEvent

from ui.main_window import WheelScrollIgnoreFilter, MainWindow
from core.character_manager import CharacterManager


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_wheel_filter_prevents_slider_value_change(qapp):
    """Verifies mouse wheel scrolling over QSlider does not alter slider value."""
    slider = QSlider(Qt.Horizontal)
    slider.setRange(0, 100)
    slider.setValue(50)

    filter_obj = WheelScrollIgnoreFilter()
    qapp.installEventFilter(filter_obj)

    try:
        # Simulate wheel event (scrolling up)
        wheel_up = QWheelEvent(
            QPointF(10, 10), QPointF(10, 10), QPoint(0, 0), QPoint(0, 120),
            Qt.NoButton, Qt.NoModifier, Qt.ScrollUpdate, False
        )
        qapp.sendEvent(slider, wheel_up)
        # Value must remain exactly 50
        assert slider.value() == 50

        # Simulate wheel event (scrolling down)
        wheel_down = QWheelEvent(
            QPointF(10, 10), QPointF(10, 10), QPoint(0, 0), QPoint(0, -120),
            Qt.NoButton, Qt.NoModifier, Qt.ScrollUpdate, False
        )
        qapp.sendEvent(slider, wheel_down)
        assert slider.value() == 50

        # Direct value change (e.g. dragging) must still work
        slider.setValue(75)
        assert slider.value() == 75
    finally:
        qapp.removeEventFilter(filter_obj)


def test_wheel_filter_prevents_spinbox_and_combobox_change(qapp):
    """Verifies mouse wheel scrolling over QSpinBox and QComboBox does not alter values."""
    spinbox = QSpinBox()
    spinbox.setRange(0, 100)
    spinbox.setValue(10)

    combobox = QComboBox()
    combobox.addItems(["Option A", "Option B", "Option C"])
    combobox.setCurrentIndex(0)

    filter_obj = WheelScrollIgnoreFilter()
    qapp.installEventFilter(filter_obj)

    try:
        wheel_ev = QWheelEvent(
            QPointF(10, 10), QPointF(10, 10), QPoint(0, 0), QPoint(0, 120),
            Qt.NoButton, Qt.NoModifier, Qt.ScrollUpdate, False
        )
        qapp.sendEvent(spinbox, wheel_ev)
        assert spinbox.value() == 10

        qapp.sendEvent(combobox, wheel_ev)
        assert combobox.currentIndex() == 0
    finally:
        qapp.removeEventFilter(filter_obj)


def test_mode_buttons_and_caption_layout(qapp):
    """Verifies ModeSegmentedControl buttons have ample width and caption has word wrap."""
    char_mgr = CharacterManager()
    win = MainWindow(character_mgr=char_mgr)

    # Verify buttons have minimum widths preventing overlap
    assert win.btn_mode_auto.minimumWidth() >= 95
    assert win.btn_mode_single.minimumWidth() >= 95

    # Verify caption label has word wrap and minimum height
    assert win.lbl_mode_caption.wordWrap() is True
    assert win.lbl_mode_caption.minimumHeight() >= 24

    win.close()
