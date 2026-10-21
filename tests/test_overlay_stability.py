"""Recorded Focus/charging regressions: masks, coordinates and lifecycle."""
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QImage

from core.movement_controller import MovementController
from overlay.transparent_overlay import TransparentOverlay
from overlay.comic_effects_overlay import ComicEffectsOverlay
from overlay.hit_test_manager import HitTestManager


@pytest.mark.parametrize("threshold", [1, 20, 45, 91, 92, 93, 94, 128, 255])
def test_mask_threshold_preserves_every_pixel_and_hole(threshold):
    image = QImage(257, 3, QImage.Format_RGBA8888)
    for y in range(3):
        for x in range(257):
            image.setPixelColor(x, y, QColor(80, 90, 100, (x + y * 77) % 256))
    region = HitTestManager(threshold).opaque_region(image)
    for y in range(3):
        for x in range(257):
            assert region.contains(QPoint(x, y)) == (image.pixelColor(x, y).alpha() >= threshold)


def test_resting_floor_does_not_oscillate_at_fractional_substeps(qapp):
    movement = MovementController()
    movement.set_bounds(QRect(-1000, -200, 1000, 800))
    movement.set_position(-600.25, 600 - movement.height)
    floor = movement.y
    for _ in range(500):
        movement._step(1 / 120)
        assert movement.y == floor
        assert movement.vy == 0
        assert movement.is_grounded


def test_effects_follow_current_coordinates_and_companion_visibility(qapp):
    movement = MovementController()
    pet = TransparentOverlay()
    effects = ComicEffectsOverlay(pet, movement)
    try:
        pet.show()
        effects.set_battery_charging(True, 99, "tom_holland")
        assert effects.isVisible()
        # Deliberately leave the widget at the old position, as signal ordering
        # did in the application. The effects must use current physics state.
        movement.x, movement.y = 600, 400
        effects.update_pet_position(600, 400)
        assert effects.x() == int(600 + pet.width() / 2 - effects.width() / 2)
        assert effects.y() == int(400 + int(pet.height() * .13) - 58)
        pet.hide()
        assert not effects.isVisible()
        effects.set_battery_charging(True, 98, "tom_holland")
        effects.show_bubble("Still hidden")
        assert not effects.isVisible()
        assert not effects._anim_timer.isActive()
        pet.show()
        assert effects.isVisible()
        assert effects._anim_timer.isActive()
        assert effects.windowFlags() & Qt.WindowTransparentForInput
        assert effects.windowFlags() & Qt.WindowDoesNotAcceptFocus
    finally:
        pet.hide()
        effects.close()
        pet.close()


def test_focus_suppresses_load_scene_but_keeps_dashboard_metrics():
    from app.application import SpiderBuddyApp
    settings = {"behavior.enable_heavy_load_scene": True, "behavior.focus_mode": True}
    app = SimpleNamespace(settings=SimpleNamespace(get=lambda k, d=None: settings.get(k, d)),
                          overlay_mgr=MagicMock(), behavior_ctrl=MagicMock(), main_window=MagicMock())
    SpiderBuddyApp._on_heavy_load_changed(app, True, 90, 86)
    app.overlay_mgr.set_heavy_load.assert_called_with(False, 90, 86)
    app.behavior_ctrl.set_heavy_load.assert_called_with(False, 90, 86)
    app.main_window.update_system_load.assert_called_with(90, 86, True)
    settings["behavior.focus_mode"] = False
    SpiderBuddyApp._on_heavy_load_changed(app, True, 90, 86)
    app.overlay_mgr.set_heavy_load.assert_called_with(True, 90, 86)
