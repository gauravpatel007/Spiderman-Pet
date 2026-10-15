"""Coordinate a single overlay with foreground ownership and visible regions."""
import os
from collections import OrderedDict
from PySide6.QtCore import QObject,Signal,QTimer
from PySide6.QtWidgets import QApplication
from .transparent_overlay import TransparentOverlay
from .web_overlay import WebOverlay
from .comic_effects_overlay import ComicEffectsOverlay
from .boundary_controller import BoundaryController
from .monitor_manager import MonitorManager
from .window_detector import WindowDetector
from .window_tracker import WindowTracker
from services.settings_service import get_settings


class OverlayManager(QObject):
    display_mode_changed=Signal(str)
    owner_changed=Signal(str)
    visibility_state_changed=Signal(bool)
    application_entered=Signal(object, bool)

    def __init__(self,movement,parent=None):
        super().__init__(parent)
        self.movement=movement
        self.settings=get_settings()
        self.monitor_mgr=MonitorManager(self)
        self.boundary_ctrl=BoundaryController(self.monitor_mgr,self)
        self.overlay=TransparentOverlay()
        self.web_overlay=WebOverlay(self.overlay, movement)
        self.comic_overlay=ComicEffectsOverlay(self.overlay, movement)
        self.overlay.set_comic_effects(self.comic_overlay)
        movement.position_changed.connect(self.comic_overlay.update_pet_position)
        self.overlay.render_size_changed.connect(self.comic_overlay.update_pet_size)
        movement.web_changed.connect(self.web_overlay.set_strand)
        movement.orientation_changed.connect(self.overlay.set_pose_rotation)
        self.window_tracker=WindowTracker(100,self)
        self._focus_timer=self.window_tracker._timer  # One shared poller.
        self._dock_state = None
        self._dock_timer = QTimer(self)
        self._dock_timer.setInterval(200)
        self._dock_timer.timeout.connect(self._refresh_dock)
        self.session_active=True
        self._running=False
        self._target_apps=self.settings.get('general.target_applications',[])
        self._display_mode=self.settings.get('general.display_mode','desktop')
        self._active_window=None
        self._positions=OrderedDict()
        self._last_origin=None
        self._last_allowed_area=None
        movement.position_changed.connect(self.overlay.update_position)
        self.overlay.render_size_changed.connect(self._on_render_size_changed)
        self.boundary_ctrl.regions_changed.connect(self._set_regions)
        self.boundary_ctrl.visibility_changed.connect(self._on_visibility_changed)
        self.window_tracker.foreground_changed.connect(self._on_foreground_changed)
        self.monitor_mgr.screens_changed.connect(self._on_screens_changed)
        self.settings.setting_changed.connect(self._on_setting_changed)

    def start(self):
        self._running=True
        self.overlay.set_character_opacity(float(self.settings.get('general.opacity',1)))
        self.overlay.set_rotation(float(self.settings.get('general.rotation',0)))
        self.overlay.set_click_through(bool(self.settings.get('system.click_through',False)))
        self.boundary_ctrl.monitor_selection=self.settings.get('general.monitor','primary')
        self.set_display_mode(self._display_mode)
        self.apply_default_position()

    def stop(self):
        self._dock_timer.stop()
        self._dock_state = None
        self._remember_position()
        self._running=False
        self.window_tracker.stop()
        self.overlay.hide()
        self.web_overlay.hide()
        self.comic_overlay.hide()
        self.owner_changed.emit('Paused')

    def _remember_position(self):
        if self._active_window and self._last_origin:
            key=(self._active_window.hwnd,self._active_window.pid)
            self._positions[key]=(self.movement.x-self._last_origin[0],self.movement.y-self._last_origin[1])
            self._positions.move_to_end(key)
            while len(self._positions)>64:
                self._positions.popitem(last=False)

    def set_display_mode(self,mode):
        if mode not in ('desktop','application'):
            return
        old_mode = self._display_mode
        self._remember_position()
        self._active_window=None
        self._last_origin=None
        self._display_mode=mode
        self.movement.allow_monitor_transitions=(mode=='desktop' and self.boundary_ctrl.monitor_selection=='all')
        self.boundary_ctrl.set_mode(mode)
        if mode=='desktop':
            self.window_tracker.stop()
            self.owner_changed.emit('Desktop — '+self.boundary_ctrl.monitor_selection)
        elif self._running:
            self.window_tracker.start()
            self.window_tracker.refresh(force=True)
        if self._running and old_mode != mode:
            self.overlay.trigger_suit_glitch(600)
            bubble_txt = "Desktop Dimension!" if mode == "desktop" else "App Focus Mode!"
            self.overlay.show_speech_bubble(f"⚡ {bubble_txt}", 2000, "glitch")
        self.display_mode_changed.emit(mode)

    def set_target_applications(self,selections):
        self._target_apps=selections
        if self._display_mode=='application':
            self.window_tracker.refresh(force=True)

    def _check_foreground_window(self):
        self.window_tracker.refresh(force=True)

    def _on_foreground_changed(self,window):
        if self._display_mode!='application':
            return
        # A context menu opened from the pet temporarily owns foreground focus.
        if window and window.pid==os.getpid() and QApplication.activePopupWidget():
            return
        self._remember_position()
        valid=window and window.is_visible and not window.is_minimized and any(
            WindowDetector.matches(window,selection) for selection in self._target_apps)
        if not valid:
            self._active_window=None
            self._last_origin=None
            self.boundary_ctrl.update_application_regions([])
            self.owner_changed.emit('Hidden — no selected application in front')
            return
        regions=self.monitor_mgr.window_regions(window.rect)
        # Keep the entire rendered companion inside the visible window.
        regions=[r for r in regions if r.width()>=self.overlay.width() and r.height()>=self.overlay.height()]
        if not regions:
            self._active_window=window
            self.boundary_ctrl.update_application_regions([])
            self.owner_changed.emit('Hidden — selected window is too small')
            return
        origin=(min(r.x() for r in regions),min(r.y() for r in regions))
        key=(window.hwnd,window.pid)
        default_x, default_y = self.default_position(regions[0])
        offset=self._positions.get(key,(default_x-origin[0], default_y-origin[1]))
        was_different = (self._active_window is None or self._active_window.hwnd != window.hwnd)
        self._active_window=window
        self._last_origin=origin
        self.boundary_ctrl.update_application_regions(regions)
        self.movement.set_position(origin[0]+offset[0],origin[1]+offset[1])
        if self._dock_state:
            self.position_activity(self._dock_state)
        self.owner_changed.emit(window.application_name or window.process_name)
        if was_different:
            self.application_entered.emit(window, True)

    def _set_regions(self,regions):
        self.movement.set_regions(regions)
        if regions:
            self._last_allowed_area=self.movement.active_region() or regions[0]

    def _on_visibility_changed(self,visible):
        is_shown = bool(visible and self.session_active and self._running and not self.settings.get('general.hidden', False))
        if is_shown:
            self.overlay.show()
        else:
            self.overlay.hide()
            self.web_overlay.hide()
        self.visibility_state_changed.emit(is_shown)

    def on_activity_changed(self, old, new):
        self.overlay.set_reading(new.value == 'focus_read')
        if old and old.value == 'title_hang' and new.value != 'title_hang':
            self.movement.orientation_changed.emit(0.0)
            self.movement.web_changed.emit(None)
        if new.value in ('title_perch', 'title_hang', 'focus_read'):
            self.position_activity(new.value)
        else:
            self._dock_state = None
            self._dock_timer.stop()

    def _refresh_dock(self):
        if not self._running or not self.session_active or not self.overlay.isVisible():
            return
        if self._dock_state and not self.position_activity(self._dock_state):
            self._dock_state = None
            self._dock_timer.stop()
            self.movement.set_motion('ground')

    def position_activity(self, name):
        if name == 'focus_read':
            area = self.movement.active_region()
            if area is None and self.movement.regions:
                area = self.movement.regions[0]
            if area is None:
                return False
            # Spider-Man sits quietly in bottom-right corner during focus reading
            x = area.x() + area.width() - self.movement.width - 24
            y = area.y() + area.height() - self.movement.height
        else:
            window = self._active_window if self._display_mode == 'application' else WindowDetector.get_foreground_window()
            if not window or not window.is_visible or window.is_minimized:
                # Find topmost visible application window
                vis = WindowDetector.get_visible_windows()
                window = vis[0] if vis else None

            if not window or not window.is_visible or window.is_minimized:
                area = self.movement.active_region()
                if area is None and self.movement.regions:
                    area = self.movement.regions[0]
                if area is None:
                    return False
            else:
                candidates = [part.intersected(allowed)
                              for part in self.monitor_mgr.window_regions(window.rect)
                              for allowed in self.movement.regions]
                candidates = [a for a in candidates if a.width() >= self.movement.width and a.height() >= self.movement.height]
                if not candidates:
                    area = self.movement.active_region()
                    if area is None and self.movement.regions:
                        area = self.movement.regions[0]
                    if area is None:
                        return False
                else:
                    area = min(candidates, key=lambda r: (r.top(), -r.right()))

            offset = max(0, min(120, int(self.settings.get('animations.title_bar_offset', 28))))
            # Position at TOP RIGHT of window, leaving room for min/max/close buttons (~140px)
            x = max(area.x() + 10, area.x() + area.width() - self.movement.width - 140)

            if name == 'title_hang':
                # Upside down hang attached to title bar
                y = min(area.y() + offset, area.y() + area.height() - self.movement.height)
            else:
                # Perch / peeking: hands clutch top horizontal bar, head peeks over
                y = area.y() - self.movement.height + offset

        self._dock_state = name
        self.movement.set_position(x, y)
        if name == 'title_hang':
            self.movement.orientation_changed.emit(180)
            cx = self.movement.x + self.movement.width / 2
            self.movement.web_changed.emit(((cx, area.y()), (cx, self.movement.y + self.movement.height * 0.18)))
        if name.startswith('title_') and not self._dock_timer.isActive():
            self._dock_timer.start()
        elif name == 'focus_read':
            self._dock_timer.stop()
        return True

    def default_position(self, area):
        width = max(0, area.width()-self.movement.width)
        height = max(0, area.height()-self.movement.height)
        choice = self.settings.get('general.default_position', 'bottom_left')
        if choice == 'custom':
            fx, fy = self.settings.get('general.custom_position', [.1, .9])
            return area.x()+max(0,min(1,float(fx)))*width, area.y()+max(0,min(1,float(fy)))*height
        x = max(0,width-16) if choice == 'bottom_right' else min(16,width)
        return area.x()+x, area.y()+height

    def apply_default_position(self):
        area = self.movement.active_region()
        if area is None and self.movement.regions:
            area = self.movement.regions[0]
        if area is not None:
            self.movement.set_position(*self.default_position(area))
            self._remember_position()

    def save_custom_position(self):
        area = self.movement.active_region() or self._last_allowed_area
        if area is None:
            return
        position = [(self.movement.x-area.x())/max(1,area.width()-self.movement.width),
                    (self.movement.y-area.y())/max(1,area.height()-self.movement.height)]
        self.settings.set('general.custom_position', position)
        self.settings.set('general.default_position', 'custom')

    def _on_render_size_changed(self,width,height):
        self.movement.set_size(width,height)
        self.movement.clamp_to_bounds()
        if self._display_mode=='application' and self._running:
            self.window_tracker.refresh(force=True)

    def _on_screens_changed(self,*args):
        if self._display_mode=='application' and self._running:
            self.window_tracker.refresh(force=True)

    def _on_setting_changed(self,key,value):
        if key=='general.hidden':
            self._on_visibility_changed(self.boundary_ctrl.is_character_visible)
        elif key=='general.default_position':
            self._positions.clear()
            self.apply_default_position()
        elif key=='general.display_mode':
            self.set_display_mode(str(value))
        elif key=='general.target_applications':
            self.set_target_applications(value)
        elif key=='general.monitor':
            self.boundary_ctrl.monitor_selection=str(value)
            if self._display_mode=='desktop':
                self.set_display_mode('desktop')
        elif key=='general.opacity':
            self.overlay.set_character_opacity(float(value))
        elif key=='general.rotation':
            self.overlay.set_rotation(float(value))
        elif key=='system.click_through':
            self.overlay.set_click_through(bool(value))
