"""Local cursor observation, bounded dragging and character controls."""
import math
import random
import time
from typing import Optional
from PySide6.QtCore import QObject, QPoint, QRect, Signal, Qt, QTimer
from PySide6.QtGui import QCursor, QGuiApplication
from PySide6.QtWidgets import QMenu, QWidgetAction, QSlider
from services.settings_service import get_settings
from .state_machine import CharacterState, CharacterState as C


def is_shift_pressed() -> bool:
    """Detect if Shift key is physically pressed in real-time, even when window lacks focus."""
    import sys
    if sys.platform == "win32":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            # Check VK_SHIFT (0x10), VK_LSHIFT (0xA0), VK_RSHIFT (0xA1)
            if (user32.GetAsyncKeyState(0x10) & 0x8000) != 0:
                return True
            if (user32.GetAsyncKeyState(0xA0) & 0x8000) != 0:
                return True
            if (user32.GetAsyncKeyState(0xA1) & 0x8000) != 0:
                return True
            return False
        except Exception:
            pass
    try:
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtCore import Qt
        return bool(QGuiApplication.keyboardModifiers() & Qt.ShiftModifier)
    except Exception:
        return False

def is_ctrl_pressed() -> bool:
    """Detect if Control key is physically pressed in real-time, even when window lacks focus."""
    import sys
    if sys.platform == "win32":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            # Check VK_CONTROL (0x11), VK_LCONTROL (0xA2), VK_RCONTROL (0xA3)
            if (user32.GetAsyncKeyState(0x11) & 0x8000) != 0:
                return True
            if (user32.GetAsyncKeyState(0xA2) & 0x8000) != 0:
                return True
            if (user32.GetAsyncKeyState(0xA3) & 0x8000) != 0:
                return True
            return False
        except Exception:
            pass
    try:
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtCore import Qt
        return bool(QGuiApplication.keyboardModifiers() & Qt.ControlModifier)
    except Exception:
        return False


class InteractionManager(QObject):
    open_dashboard_requested = Signal()
    open_sticky_notes_requested = Signal()
    quit_requested = Signal()
    trampoline_created = Signal(object, object)  # (p1: QPointF, p2: QPointF)

    def __init__(self, state_machine, movement, character_mgr, animation=None, behavior=None, parent=None):
        super().__init__(parent)
        self.state_machine, self.movement, self.character_mgr = state_machine, movement, character_mgr
        self.animation, self.behavior = animation, behavior
        self._ctrl_trampoline_drag = False
        self._trampoline_start = None
        self.settings = get_settings()
        self.overlay = None
        self._is_dragging = False
        self._shift_drag = False
        self._is_title_hang_drag = False
        self._title_hang_activity = None
        self._is_ground_sit_drag = False
        self._ground_sit_press_pos = None
        self._ground_sit_start_x = 0
        self._ground_sit_start_y = 0
        self._title_hang_press_pos = None
        self._title_hang_start_x = 0
        self._title_hang_start_y = 0
        self._title_hang_detached = False
        self.overlay_mgr = None
        self._drag_offset = QPoint()
        self._last_cursor = None
        self._last_sample = time.monotonic()
        self._last_reaction = 0.0
        self._last_dodge_time = 0.0
        self._nearby = self._menu_open = False
        self._drag_history = []
        self._last_follow_jump = 0.0
        self.movement.boundary_hit.connect(self._on_movement_boundary_hit)
        self._cursor_timer = QTimer(self)
        self._cursor_timer.setInterval(75)
        self._cursor_timer.timeout.connect(self._track_cursor)

    def _on_movement_boundary_hit(self, contact: str) -> None:
        """Handle dynamic physics boundary reactions (safety web catch, ricochet, landing)."""
        if contact == 'safety_web_catch':
            if self.overlay and hasattr(self.overlay, "show_speech_bubble"):
                self.overlay.show_speech_bubble("THWIP! 🕸️ Safety catch!", 1600, "action")
        elif contact == 'fling_land':
            self.state_machine.transition_to(C.LAND, force=True)
            if self.overlay and hasattr(self.overlay, "show_speech_bubble"):
                quotes = ["Nailed the landing! 🕷️", "Smooth landing! 😎", "Sticky feet! 🕸️", "Safe and sound! 🕷️"]
                self.overlay.show_speech_bubble(random.choice(quotes), 1600, "comic")
        elif contact in ('left_wall', 'right_wall', 'ceiling') and getattr(self.movement, 'mode', '') == 'fling':
            if self.overlay and hasattr(self.overlay, "show_speech_bubble"):
                self.overlay.show_speech_bubble(random.choice(["BOING! 💥", "RICOCHET! ⚡", "WHOA! 💥"]), 1200, "action")

    def start(self):
        self._last_cursor = None
        self._cursor_timer.start()

    def stop(self):
        self._cursor_timer.stop()
        self._last_cursor = None
        self._nearby = False
        self.behavior.cursor_attention = False

    def handle_mouse_press(self, global_pos, local_pos, button):
        if button != Qt.LeftButton and button != 1:
            return False

        self._drag_history.clear()
        self._drag_history.append((time.monotonic(), float(global_pos.x()), float(global_pos.y())))

        # Interactive Web Trampoline: holding Ctrl + Drag draws a spring trampoline!
        if is_ctrl_pressed() and self.settings.get("behavior.enable_web_trampoline", True):
            from PySide6.QtCore import QPointF
            self._ctrl_trampoline_drag = True
            self._trampoline_start = QPointF(float(global_pos.x()), float(global_pos.y()))
            self.movement.web_changed.emit((
                (self._trampoline_start.x(), self._trampoline_start.y()),
                (self._trampoline_start.x(), self._trampoline_start.y()),
            ))
            if self.overlay and hasattr(self.overlay, "show_speech_bubble"):
                self.overlay.show_speech_bubble("🕸️ Drag to draw Web Trampoline!", 1400, "comic")
            return True

        is_shift = is_shift_pressed()
        self._shift_drag = is_shift
        # If user moves him normally without Shift, unpin him!
        if not is_shift and hasattr(self.behavior, "set_pinned") and getattr(self.behavior, "_is_pinned", False):
            self.behavior.set_pinned(False)

        # Check if currently attached to title bar (title_hang or title_perch)
        if self.state_machine.current_state in (C.TITLE_HANG, C.TITLE_PERCH):
            self._is_title_hang_drag = True
            self._title_hang_activity = self.state_machine.current_state
            self._title_hang_press_pos = global_pos
            self._title_hang_start_x = self.movement.x
            self._title_hang_start_y = self.movement.y
            self._title_hang_detached = False
            self._drag_offset = local_pos
            self._is_dragging = self.movement.is_dragging = True
            if self.behavior:
                self.behavior.user_override()
            self.movement.set_motion("hold", 0.0, 0.0)
            return True

        # Check if currently sitting on the ground (ground sit drag like title perch)
        if self.state_machine.current_state == C.SIT and self.settings.get("behavior.enable_ground_sit_drag", True):
            self._is_ground_sit_drag = True
            self._ground_sit_press_pos = global_pos
            self._ground_sit_start_x = self.movement.x
            self._ground_sit_start_y = self.movement.y
            self._drag_offset = local_pos
            self._is_dragging = self.movement.is_dragging = True
            if self.behavior:
                self.behavior.user_override()
            self.movement.set_motion("hold", 0.0, 0.0)
            return True

        if self.behavior:
            self.behavior.user_override()
        self._is_dragging = self.movement.is_dragging = True
        self._drag_offset = local_pos
        self.state_machine.transition_to(C.DRAGGED, force=True)
        return True

    def handle_mouse_move(self, global_pos):
        if self._ctrl_trampoline_drag and self._trampoline_start is not None:
            self.movement.web_changed.emit((
                (self._trampoline_start.x(), self._trampoline_start.y()),
                (float(global_pos.x()), float(global_pos.y())),
            ))
            return True

        if not self._is_dragging:
            return False

        if self._is_title_hang_drag:
            # Check downward pull distance and horizontal movement
            press_pos = self._title_hang_press_pos or global_pos
            dx = global_pos.x() - press_pos.x()
            dy = global_pos.y() - press_pos.y()

            # Detach ONLY on an intentional downward yank (> 70px and predominantly vertical dy > 1.8 * abs(dx)):
            # While dragging horizontally left-to-right, he will NEVER fall to the ground!
            if dy > 70 and dy > 1.8 * abs(dx):
                self._is_title_hang_drag = False
                self._title_hang_detached = True
                self._is_dragging = self.movement.is_dragging = False

                # Reset orientation to upright and clear web line
                self.movement.orientation_changed.emit(0.0)
                self.movement.web_changed.emit(None)

                # Stop docking timer in overlay manager if present
                if hasattr(self, 'overlay_mgr') and self.overlay_mgr:
                    self.overlay_mgr._dock_state = None
                    self.overlay_mgr._dock_timer.stop()
                    self.overlay_mgr._dock_relative_x = None
                    self.overlay_mgr._dock_area = None

                # Visual comic bubble feedback
                if self.overlay and hasattr(self.overlay, "show_speech_bubble"):
                    self.overlay.show_speech_bubble("WHOA! 🕸️ Detached!", 1600, "action")

                # Transition to FALL state with physics gravity!
                self.movement.set_motion("jump", 0.0, 30.0)
                self.state_machine.transition_to(C.FALL, force=True)
                return True

            # Dragging horizontally along the TOP bar without falling to the ground:
            dock_area = None
            if hasattr(self, 'overlay_mgr') and self.overlay_mgr and getattr(self.overlay_mgr, '_dock_area', None):
                dock_area = self.overlay_mgr._dock_area
            elif self.movement.active_region():
                dock_area = self.movement.active_region()
            elif self.movement.regions:
                dock_area = self.movement.regions[0]

            new_x = global_pos.x() - self._drag_offset.x()
            if dock_area is not None:
                min_x = dock_area.x() + 8
                max_x = max(min_x, dock_area.x() + dock_area.width() - self.movement.width - 8)
                new_x = max(min_x, min(max_x, new_x))

            offset = max(0, min(120, int(self.settings.get('animations.title_bar_offset', 28))))
            activity = getattr(self, '_title_hang_activity', self.state_machine.current_state)

            if activity == C.TITLE_PERCH:
                # Key 7 (title_perch): retains title_perch across entire horizontal drag
                perch_y = (dock_area.y() if dock_area else 0) - self.movement.height + offset
                self.movement.set_position(new_x, perch_y)
                self.movement.orientation_changed.emit(0.0)
                self.movement.web_changed.emit(None)
                if self.state_machine.current_state != C.TITLE_PERCH:
                    self.state_machine.transition_to(C.TITLE_PERCH, force=True)
                if hasattr(self, 'overlay_mgr') and self.overlay_mgr:
                    self.overlay_mgr._dock_state = 'title_perch'
                    self.overlay_mgr.update_dock_drag_position(new_x)
            else:
                # Key 6 (title_hang): retains title_hang across entire horizontal drag
                hang_y = (dock_area.y() if dock_area else 0) + offset
                elastic_y = hang_y + max(-4.0, min(8.0, dy * 0.15))
                self.movement.set_position(new_x, elastic_y)
                self.movement.orientation_changed.emit(180.0)
                cx = new_x + self.movement.width / 2.0
                top_anchor_y = dock_area.y() if dock_area is not None else (hang_y - offset)
                attach_y = elastic_y + self.movement.height * 0.18
                self.movement.web_changed.emit(((cx, top_anchor_y), (cx, attach_y)))
                if self.state_machine.current_state != C.TITLE_HANG:
                    self.state_machine.transition_to(C.TITLE_HANG, force=True)
                if hasattr(self, 'overlay_mgr') and self.overlay_mgr:
                    self.overlay_mgr._dock_state = 'title_hang'
                    self.overlay_mgr.update_dock_drag_position(new_x)

            return True

        if self._is_ground_sit_drag:
            press_pos = self._ground_sit_press_pos or global_pos
            dx = global_pos.x() - press_pos.x()
            dy = global_pos.y() - press_pos.y()

            # Detach ONLY on an intentional upward pull (> 65px and predominantly vertical dy < -65 and abs(dy) > 1.6 * abs(dx)):
            if dy < -65 and abs(dy) > 1.6 * abs(dx):
                self._is_ground_sit_drag = False
                self._is_dragging = self.movement.is_dragging = False
                if self.overlay and hasattr(self.overlay, "show_speech_bubble"):
                    self.overlay.show_speech_bubble("HUP! 🕷️ Up we go!", 1400, "action")
                self.movement.set_motion("jump", 0.0, -180.0)
                self.state_machine.transition_to(C.JUMP, force=True)
                return True

            # Dragging horizontally along the GROUND / TASKBAR:
            active_area = self.movement.active_region() or (self.movement.regions[0] if self.movement.regions else None)
            new_x = global_pos.x() - self._drag_offset.x()
            if active_area is not None:
                min_x = active_area.left() + 4
                max_x = max(min_x, active_area.right() - self.movement.width - 4)
                new_x = max(min_x, min(max_x, new_x))

            ground_y = (active_area.bottom() - self.movement.height + 1) if active_area is not None else self._ground_sit_start_y
            self.movement.set_position(new_x, ground_y)
            self.movement.orientation_changed.emit(0.0)
            self.movement.web_changed.emit(None)
            if self.state_machine.current_state != C.SIT:
                self.state_machine.transition_to(C.SIT, force=True)
            return True

        if is_shift_pressed():
            self._shift_drag = True
        self._drag_history.append((time.monotonic(), float(global_pos.x()), float(global_pos.y())))
        if len(self._drag_history) > 30:
            self._drag_history = self._drag_history[-30:]
        self.movement.set_position(global_pos.x()-self._drag_offset.x(), global_pos.y()-self._drag_offset.y())
        return True

    def handle_mouse_release(self, button):
        if button != Qt.LeftButton:
            return False

        if self._ctrl_trampoline_drag and self._trampoline_start is not None:
            from PySide6.QtCore import QPointF
            self._ctrl_trampoline_drag = False
            self.movement.web_changed.emit(None)
            cur = QPointF(float(self._last_cursor.x() if self._last_cursor else self.movement.x),
                          float(self._last_cursor.y() if self._last_cursor else self.movement.y))
            # If cursor didn't move far, use current mouse pos from QCursor
            p2 = QPointF(float(QCursor.pos().x()), float(QCursor.pos().y()))
            dx = p2.x() - self._trampoline_start.x()
            dy = p2.y() - self._trampoline_start.y()
            if math.hypot(dx, dy) >= 30.0:
                self.trampoline_created.emit(self._trampoline_start, p2)
                if self.overlay and hasattr(self.overlay, "show_speech_bubble"):
                    self.overlay.show_speech_bubble("🕸️ Trampoline set! Ready to bounce!", 1800, "action")
            else:
                # Ctrl + Click without dragging: shoot web line to cursor!
                if self.settings.get("behavior.enable_web_shoot_cursor", True):
                    self.shoot_web_at_cursor(QCursor.pos())
            self._trampoline_start = None
            return True

        if not self._is_dragging:
            return False

        if self._is_ground_sit_drag:
            self._is_ground_sit_drag = False
            self._is_dragging = self.movement.is_dragging = False

            # Settle firmly on the ground in SIT posture!
            active_area = self.movement.active_region() or (self.movement.regions[0] if self.movement.regions else None)
            if active_area is not None:
                ground_y = active_area.y() + active_area.height() - self.movement.height
                self.movement.set_position(self.movement.x, ground_y)
            self.state_machine.transition_to(C.SIT, force=True)
            if hasattr(self.behavior, "set_pinned"):
                self.behavior.set_pinned(True, keep_state=True)
            if self.overlay and hasattr(self.overlay, "show_speech_bubble"):
                self.overlay.show_speech_bubble("Chilling right here! 😎", 1600, "comic")
            return True

        if self._is_title_hang_drag:
            self._is_title_hang_drag = False
            self._is_dragging = self.movement.is_dragging = False

            press_pos = self._title_hang_press_pos or QPoint(int(self.movement.x), int(self.movement.y))
            cursor_pos = QCursor.pos() if hasattr(QCursor, 'pos') else press_pos
            dx = cursor_pos.x() - press_pos.x()
            dy = cursor_pos.y() - press_pos.y()

            if dy > 70 and dy > 1.8 * abs(dx):
                # Detached downward!
                self.movement.orientation_changed.emit(0.0)
                self.movement.web_changed.emit(None)
                if hasattr(self, 'overlay_mgr') and self.overlay_mgr:
                    self.overlay_mgr._dock_state = None
                    if hasattr(self.overlay_mgr, '_dock_timer') and hasattr(self.overlay_mgr._dock_timer, 'stop'):
                        self.overlay_mgr._dock_timer.stop()
                    self.overlay_mgr._dock_relative_x = None
                    self.overlay_mgr._dock_area = None
                self.movement.set_motion("jump", 0.0, 30.0)
                self.state_machine.transition_to(C.FALL, force=True)
                return True

            # Otherwise, securely locked on the title bar at the current position!
            dock_area = None
            if hasattr(self, 'overlay_mgr') and self.overlay_mgr and getattr(self.overlay_mgr, '_dock_area', None):
                dock_area = self.overlay_mgr._dock_area
            elif self.movement.active_region():
                dock_area = self.movement.active_region()
            elif self.movement.regions:
                dock_area = self.movement.regions[0]

            offset = max(0, min(120, int(self.settings.get('animations.title_bar_offset', 28))))

            if hasattr(self, 'overlay_mgr') and self.overlay_mgr:
                self.overlay_mgr.update_dock_drag_position(self.movement.x)

            activity = getattr(self, '_title_hang_activity', self.state_machine.current_state)
            if activity == C.TITLE_PERCH:
                # Key 7 (title_perch)
                perch_y = (dock_area.y() if dock_area else 0) - self.movement.height + offset
                self.movement.set_position(self.movement.x, perch_y)
                self.movement.orientation_changed.emit(0.0)
                self.movement.web_changed.emit(None)
                self.movement.set_motion("hold", 0.0, 0.0)
                if self.state_machine.current_state != C.TITLE_PERCH:
                    self.state_machine.transition_to(C.TITLE_PERCH, force=True)
                if hasattr(self, 'overlay_mgr') and self.overlay_mgr:
                    self.overlay_mgr._dock_state = 'title_perch'
                    if hasattr(self.overlay_mgr, '_dock_timer') and hasattr(self.overlay_mgr._dock_timer, 'isActive') and not self.overlay_mgr._dock_timer.isActive():
                        self.overlay_mgr._dock_timer.start()
                if self.overlay and hasattr(self.overlay, "show_speech_bubble"):
                    self.overlay.show_speech_bubble("👀 Window title secured! Perching tight!", 1600, "action")
            else:
                # Key 6 (title_hang)
                hang_y = (dock_area.y() if dock_area else 0) + offset
                self.movement.set_position(self.movement.x, hang_y)
                cx = self.movement.x + self.movement.width / 2.0
                top_y = dock_area.y() if dock_area is not None else (hang_y - offset)
                attach_y = hang_y + self.movement.height * 0.18
                self.movement.web_changed.emit(((cx, top_y), (cx, attach_y)))
                self.movement.orientation_changed.emit(180.0)
                self.movement.set_motion("hold", 0.0, 0.0)
                if self.state_machine.current_state != C.TITLE_HANG:
                    self.state_machine.transition_to(C.TITLE_HANG, force=True)
                if hasattr(self, 'overlay_mgr') and self.overlay_mgr:
                    self.overlay_mgr._dock_state = 'title_hang'
                    if hasattr(self.overlay_mgr, '_dock_timer') and hasattr(self.overlay_mgr._dock_timer, 'isActive') and not self.overlay_mgr._dock_timer.isActive():
                        self.overlay_mgr._dock_timer.start()
                if self.overlay and hasattr(self.overlay, "show_speech_bubble"):
                    self.overlay.show_speech_bubble("🕸️ Top bar secured! Hanging tight!", 1600, "comic")
            return True

        self._is_dragging = self.movement.is_dragging = False

        # Persist last position so companion reopens where left
        try:
            self.settings.set('general.last_position', [float(self.movement.x), float(self.movement.y)], auto_save=False)
        except Exception:
            pass

        is_shift = is_shift_pressed() or self._shift_drag

        # 🚀 1. Check Drag-and-Throw (Fling Physics)
        now = time.monotonic()
        if (
            not is_shift
            and self.settings.get('behavior.enable_fling_physics', True)
            and len(self._drag_history) >= 2
        ):
            recent = [p for p in self._drag_history if (now - p[0]) <= 0.16]
            if len(recent) >= 2:
                p_old = recent[0]
                p_new = recent[-1]
                dt = max(0.02, p_new[0] - p_old[0])
                vx = (p_new[1] - p_old[1]) / dt
                vy = (p_new[2] - p_old[2]) / dt
                fling_speed = math.hypot(vx, vy)
                if fling_speed >= 380.0:
                    self._drag_history.clear()
                    self._shift_drag = False
                    self.movement.set_fling_physics(vx, vy)
                    self.state_machine.transition_to(C.JUMP if vy < -120 else C.FALL, force=True)
                    if self.overlay and hasattr(self.overlay, "show_speech_bubble"):
                        quotes = ["WHOOSH! 🚀", "YAAAAHOO! 🚀", "WHEEEE! 🚀", "HOLD ON! 🚀", "THWIP! 🚀"]
                        self.overlay.show_speech_bubble(random.choice(quotes), 1600, "action")
                    return True
        self._drag_history.clear()

        if is_shift and hasattr(self.behavior, "set_pinned"):
            # Shift+drag: lock in place, no activities, hold position!
            self.behavior.set_pinned(True)
        else:
            # Check if dragged to the top-most side (ceiling / window title bar)
            active_area = self.movement.active_region() or (self.movement.regions[0] if self.movement.regions else None)
            is_topmost = False
            if active_area is not None:
                is_topmost = (self.movement.y <= active_area.y() + 85)
            else:
                is_topmost = (self.movement.y <= 85)

            if is_topmost:
                area = active_area or QRect(0, 0, 1920, 1080)
                avail_w = max(1, area.width() - self.movement.width)
                rel_x = max(0.0, min(1.0, (self.movement.x - area.x()) / avail_w))
                offset = max(0, min(120, int(self.settings.get('animations.title_bar_offset', 28))))

                if hasattr(self, 'overlay_mgr') and self.overlay_mgr:
                    self.overlay_mgr._dock_relative_x = rel_x
                    self.overlay_mgr._dock_area = area

                if rel_x >= 0.75:
                    # 25% area from right side: Key 7 (title_perch)
                    perch_y = area.y() - self.movement.height + offset
                    self.movement.set_position(self.movement.x, perch_y)
                    self.movement.orientation_changed.emit(0.0)
                    self.movement.web_changed.emit(None)
                    self.movement.set_motion("hold", 0.0, 0.0)
                    if hasattr(self, 'overlay_mgr') and self.overlay_mgr:
                        self.overlay_mgr._dock_state = 'title_perch'
                        if hasattr(self.overlay_mgr, '_dock_timer') and hasattr(self.overlay_mgr._dock_timer, 'isActive') and not self.overlay_mgr._dock_timer.isActive():
                            self.overlay_mgr._dock_timer.start()
                    self.state_machine.transition_to(C.TITLE_PERCH, force=True)
                    if self.overlay and hasattr(self.overlay, "show_speech_bubble"):
                        self.overlay.show_speech_bubble("👀 Window title secured! Perching tight!", 1800, "action")
                else:
                    # 75% area from left side: Key 6 (title_hang)
                    hang_y = area.y() + offset
                    self.movement.set_position(self.movement.x, hang_y)
                    self.movement.orientation_changed.emit(180.0)
                    cx = self.movement.x + self.movement.width / 2.0
                    top_y = area.y()
                    attach_y = hang_y + self.movement.height * 0.18
                    self.movement.web_changed.emit(((cx, top_y), (cx, attach_y)))
                    self.movement.set_motion("hold", 0.0, 0.0)
                    if hasattr(self, 'overlay_mgr') and self.overlay_mgr:
                        self.overlay_mgr._dock_state = 'title_hang'
                        if hasattr(self.overlay_mgr, '_dock_timer') and hasattr(self.overlay_mgr._dock_timer, 'isActive') and not self.overlay_mgr._dock_timer.isActive():
                            self.overlay_mgr._dock_timer.start()
                    self.state_machine.transition_to(C.TITLE_HANG, force=True)
                    if self.overlay and hasattr(self.overlay, "show_speech_bubble"):
                        self.overlay.show_speech_bubble("🕸️ Top bar secured! Hanging tight!", 1800, "comic")
            else:
                # Check if dropped firmly at the ground floor (sitting posture as in reference photo)
                is_near_floor = active_area is not None and (self.movement.y >= active_area.y() + active_area.height() - self.movement.height - 40)
                if is_near_floor:
                    ground_y = active_area.y() + active_area.height() - self.movement.height
                    self.movement.set_position(self.movement.x, ground_y)
                    self.movement.orientation_changed.emit(0.0)
                    self.movement.web_changed.emit(None)
                    self.movement.set_motion("hold", 0.0, 0.0)
                    self.state_machine.transition_to(C.SIT, force=True)
                    if hasattr(self.behavior, "set_pinned"):
                        self.behavior.set_pinned(True, keep_state=True)
                    if self.overlay and hasattr(self.overlay, "show_speech_bubble"):
                        self.overlay.show_speech_bubble("Chilling on the floor! 🕷️", 1800, "comic")
                else:
                    self.state_machine.transition_to(C.LAND if self.movement.is_grounded else C.FALL, force=True)

        self._shift_drag = False
        return True

    def spawn_trampoline_below(self, width_px: float = 240.0, offset_y: float = 90.0) -> None:
        """Spawn an active web trampoline right below Spider-Man."""
        if not self.settings.get("behavior.enable_web_trampoline", True):
            return
        from PySide6.QtCore import QPointF
        center_x = self.movement.x + self.movement.width * 0.5
        feet_y = self.movement.y + self.movement.height
        p1 = QPointF(center_x - width_px * 0.5, feet_y + offset_y)
        p2 = QPointF(center_x + width_px * 0.5, feet_y + offset_y)
        self.trampoline_created.emit(p1, p2)
        if self.overlay and hasattr(self.overlay, "show_speech_bubble"):
            self.overlay.show_speech_bubble("🕸️ Trampoline set below! Jump on it!", 1800, "action")

    def create_desktop_sticky_note(self, pos=None):
        """Spawn a new web-hanging desktop sticky note near Spider-Man."""
        if hasattr(self, 'overlay_mgr') and self.overlay_mgr and hasattr(self.overlay_mgr, 'sticky_notes_mgr'):
            spawn_pos = pos or QPoint(int(self.movement.x + self.movement.width + 16), int(max(40, self.movement.y - 120)))
            self.overlay_mgr.sticky_notes_mgr.create_new_note(title="Spider Mission Note", pos=spawn_pos)
            if self.overlay and hasattr(self.overlay, "show_speech_bubble"):
                self.overlay.show_speech_bubble("🕸️ Sticky note created! Keep your goals in sight!", 2000, "comic")

    def toggle_desktop_sticky_notes(self):
        """Toggle desktop visibility of all floating notes."""
        if hasattr(self, 'overlay_mgr') and self.overlay_mgr and hasattr(self.overlay_mgr, 'sticky_notes_mgr'):
            self.overlay_mgr.sticky_notes_mgr.toggle_all_visibility()

    def open_sticky_notes_dashboard(self):
        """Open dashboard and switch to Sticky Notes tab."""
        self.open_dashboard_requested.emit()
        self.open_sticky_notes_requested.emit()

    def play_activity(self, state: CharacterState, force: bool = True):
        """Request a permitted activity; recovery transitions remain backend-owned."""
        if not force and not self.behavior.activity_enabled(state):
            return
        if not self.animation.has_animation(state.value):
            return
        if not force and self.settings.get("behavior.focus_mode", False) and state.value not in ("idle", "sit", "sleep", "focus_read"):
            return
        if hasattr(self.behavior, "set_pinned") and getattr(self.behavior, "_is_pinned", False):
            self.behavior.set_pinned(False)
        self.behavior.user_override()
        if state.value in ('title_perch', 'title_hang', 'focus_read'):
            if hasattr(self.behavior, 'position_activity'):
                self.behavior.position_activity(state.value)
        self.state_machine.transition_to(state, force=True)

    def _request(self, state):
        if hasattr(self.behavior, "set_pinned") and getattr(self.behavior, "_is_pinned", False):
            self.behavior.set_pinned(False)
        is_override = time.monotonic() < self.behavior._override_until
        if not self.behavior.activity_enabled(state):
            return
        if not self.animation.has_animation(state.value) and state.value not in ('title_perch', 'title_hang', 'focus_read'):
            return
        self.behavior.user_override()
        if state.value in ('title_perch', 'title_hang', 'focus_read'):
            if hasattr(self.behavior, 'position_activity'):
                self.behavior.position_activity(state.value)
        self.state_machine.transition_to(state, force=True)

    def handle_click(self):
        if not self._is_dragging:
            if hasattr(self.behavior, "_is_pinned") and getattr(self.behavior, "_is_pinned", False):
                if self.overlay and hasattr(self.overlay, "show_speech_bubble"):
                    self.overlay.show_speech_bubble("📌 Pinned in place! Drag to move me.", 1800, "comic")
                return
            if self.state_machine.current_state == C.TITLE_HANG:
                if self.overlay and hasattr(self.overlay, "show_speech_bubble"):
                    quotes = ["🕸️ Just hanging around!", "Upside down is the best view!", "All blood rushing to my head!", "THWIP!"]
                    self.overlay.show_speech_bubble(random.choice(quotes), 1800, "comic")
                return
            self._request(C.WAVE)
            if self.overlay and hasattr(self.overlay, "show_speech_bubble"):
                quotes = ["THWIP!", "Hey there!", "Careful with the suit!", "Need a web?", "Spider-Buddy reporting!"]
                self.overlay.show_speech_bubble(random.choice(quotes), 1800, "comic")

    def handle_double_click(self):
        self._is_dragging = self.movement.is_dragging = False
        # Open app window on double-click
        if self.overlay and hasattr(self.overlay, "show_speech_bubble"):
            self.overlay.show_speech_bubble("Opening Spider-Hub!", 1800, "action")
        self.open_dashboard_requested.emit()

    def shoot_web_at(self, target_pos: QPoint):
        """Phase 10.3: Shoot a visible web line toward the given point with THWIP effect."""
        facing = float(target_pos.x()) < (self.movement.x + self.movement.width * 0.5)
        self.movement.is_facing_left = facing
        self.animation.set_facing_left(facing)
        hand_x = self.movement.x + (self.movement.width * (0.25 if facing else 0.75))
        hand_y = self.movement.y + self.movement.height * 0.38
        strand = ((hand_x, hand_y), (float(target_pos.x()), float(target_pos.y())))
        self.movement.web_changed.emit(strand)
        QTimer.singleShot(480, lambda: self.movement.web_changed.emit(None))
        self._request(C.WAVE)
        if self.overlay and hasattr(self.overlay, "show_speech_bubble"):
            thwips = ["THWIP! 🕸️", "THWIP! 🎯", "Gotcha! 🕸️", "Bullseye! 🎯"]
            self.overlay.show_speech_bubble(random.choice(thwips), 1400, "action")

    def shoot_web_at_cursor(self, cursor_pos: Optional[QPoint] = None):
        """Shoot a high-velocity web strand toward the mouse cursor with comic THWIP! effect."""
        target = cursor_pos or QCursor.pos()
        self.shoot_web_at(target)

    def _track_cursor(self):
        if (
            self._is_dragging
            or self._menu_open
            or not self.overlay
            or not self.overlay.isVisible()
            or not self.settings.get('behavior.enable_mouse_following', True)
            or self.settings.get('behavior.focus_mode', False)
            or self.state_machine.current_state == C.FOCUS_READ
            or getattr(self.behavior, "_is_pinned", False)
        ):
            self._last_cursor = None
            self._nearby = False
            self.behavior.cursor_attention = self._menu_open
            return
        point = QCursor.pos()
        now = time.monotonic()
        elapsed = max(.01, now - self._last_sample)

        # 1. Calculate cursor velocity vector
        if self._last_cursor is not None and elapsed > 0.001:
            vx_cursor = (point.x() - self._last_cursor.x()) / elapsed
            vy_cursor = (point.y() - self._last_cursor.y()) / elapsed
            cursor_speed = math.hypot(vx_cursor, vy_cursor)
        else:
            vx_cursor = vy_cursor = cursor_speed = 0.0

        self._last_sample, self._last_cursor = now, point

        center_x = self.movement.x + self.movement.width / 2.0
        center_y = self.movement.y + self.movement.height / 2.0
        center = QPoint(round(center_x), round(center_y))

        to_pet_x = center_x - point.x()
        to_pet_y = center_y - point.y()
        dist_to_pet = math.hypot(to_pet_x, to_pet_y)

        # Approach vector alignment: dot product > 0 means moving toward Spider-Man
        dot = (vx_cursor * to_pet_x + vy_cursor * to_pet_y)
        approach_align = dot / (cursor_speed * dist_to_pet) if (cursor_speed > 0 and dist_to_pet > 0) else 0.0

        # ⚡ SPIDER-SENSE DODGING TRIGGER:
        # Rapid approach toward Spider-Man within reaction proximity
        is_rapid_approach = (dist_to_pet < 220.0 and cursor_speed > 600.0 and approach_align > 0.35)
        can_dodge = (
            bool(self.settings.get('behavior.enable_spider_sense_dodging', True))
            and not getattr(self.behavior, "_is_pinned", False)
            and not self._is_dragging
            and not self._menu_open
            and self.state_machine.current_state not in (C.DRAGGED, C.SLEEP, C.TITLE_HANG, C.TITLE_PERCH)
            and (now - self._last_dodge_time >= 1.8)
        )

        if is_rapid_approach and can_dodge:
            self._last_dodge_time = now

            # 1. Comic-style Spider-Sense squiggles (⚡) flash over his head
            if self.overlay and hasattr(self.overlay, "trigger_spider_sense"):
                self.overlay.trigger_spider_sense(duration_ms=800)

            # 2. Pop-up comic dialogue / reaction bubble
            if self.overlay and hasattr(self.overlay, "show_speech_bubble"):
                dodges = ["⚡ SPIDER-SENSE!", "⚡ WHOOSH!", "⚡ TOO SLOW!", "⚡ NICE TRY!", "⚡ WHOA!", "⚡ NOT TODAY!"]
                self.overlay.show_speech_bubble(random.choice(dodges), duration_ms=1800, style="action")

            # 3. Determine dodge direction away from incoming cursor
            dodge_dir = 1.0 if (point.x() < center_x) else -1.0
            active_area = self.movement.active_region()
            if active_area:
                if self.movement.x > active_area.right() - self.movement.width - 120:
                    dodge_dir = -1.0
                elif self.movement.x < active_area.left() + 120:
                    dodge_dir = 1.0

            dodge_vx = dodge_dir * random.uniform(420.0, 560.0)
            dodge_vy = random.uniform(-480.0, -620.0)  # acrobatic hop/flip upward

            self.behavior.user_override()
            self.movement.is_facing_left = (dodge_dir < 0)
            self.animation.set_facing_left(dodge_dir < 0)
            self.movement.set_motion("jump", horizontal=dodge_vx, vertical=dodge_vy)
            self.state_machine.transition_to(C.JUMP, force=True)
            return

        # 🎯 Mouse Chase / Follow Mode:
        # Spider-Man actively approaches the mouse cursor while you work
        safe = self.state_machine.current_state in (C.IDLE, C.WALK, C.RUN, C.SIT, C.WAVE)
        if safe:
            facing = (point.x() < center_x)
            self.movement.is_facing_left = facing
            self.animation.set_facing_left(facing)

            if dist_to_pet > 160.0:
                # Walk/hop towards mouse cursor
                chase_speed = 135.0 if not is_shift_pressed() else 230.0
                if self.movement.is_grounded:
                    self.movement.set_motion('ground', horizontal=(-chase_speed if facing else chase_speed))
                    if self.state_machine.current_state not in (C.WALK, C.RUN):
                        self.state_machine.transition_to(C.WALK)

                    # If cursor is high up above Spider-Man, do an acrobatic leap towards it
                    if to_pet_y > 180 and (now - self._last_follow_jump) > 3.2:
                        self._last_follow_jump = now
                        jump_vx = -160.0 if facing else 160.0
                        self.movement.set_motion("jump", horizontal=jump_vx, vertical=-460.0)
                        self.state_machine.transition_to(C.JUMP, force=True)
            else:
                # Arrived close to cursor: stop and observe
                if self.movement.is_grounded and self.movement.vx != 0.0:
                    self.movement.set_motion('ground', horizontal=0.0)
                if self.state_machine.current_state in (C.WALK, C.RUN):
                    self.state_machine.transition_to(C.IDLE, force=True)
                if cursor_speed > 300 and now - self._last_reaction > 8 and random.random() < 0.25:
                    self._last_reaction = now
                    self._request(C.WAVE)

        nearby = (dist_to_pet <= 180.0)
        self.behavior.cursor_attention = nearby and safe
        if self._nearby and not nearby:
            self.behavior.resume_autonomy()
        self._nearby = nearby

    def show_context_menu(self, global_pos):
        menu = QMenu()
        menu.setStyleSheet('QMenu { background: #1A1A24; color: white; padding: 6px; }'
                          'QMenu::item { padding: 6px 20px; }'
                          'QMenu::item:selected { background: #B50920; }'
                          'QMenu::item:disabled { color: #777; }')
        menu.addAction('SPIDER-BUDDY').setEnabled(False)
        for label, state in [('Wake Up', C.WAKE_UP), ('Sit Down', C.SIT), ('Sleep', C.SLEEP),
                             ('Walk', C.WALK), ('Run', C.RUN), ('Jump', C.JUMP),
                             ('Web Swing', C.SWING), ('Dance', C.DANCE)]:
            action = menu.addAction(label)
            enabled = self.behavior.activity_enabled(state) and self.animation.has_animation(state.value)
            if state == C.SWING:
                enabled = enabled and self.settings.get('behavior.enable_swinging', True)
                area = self.movement.active_region()
                room = min(self.movement.y+self.movement.height/2-area.top()-12,
                           area.height()*.65, area.width()*.4) if area else 0
                enabled = enabled and room >= self.movement.height*.6
            action.setEnabled(enabled)
            action.triggered.connect(lambda checked=False, state=state: self._request(state))

        shoot_cursor_act = menu.addAction('🎯 Shoot Web at Mouse Cursor')
        shoot_cursor_act.triggered.connect(lambda: self.shoot_web_at_cursor(global_pos))
        web_act = menu.addAction('🕸️ Shoot Web Here')
        web_act.triggered.connect(lambda: self.shoot_web_at(global_pos))
        tramp_act = menu.addAction('🕸️ Web Trampoline (Spawn below me)')
        tramp_act.triggered.connect(lambda: self.spawn_trampoline_below())

        # Spider Sticky Notes Sub-menu
        notes_menu = menu.addMenu('📝 Spider Sticky Notes')
        enable_notes_act = notes_menu.addAction('📌 Enable Sticky Notes')
        enable_notes_act.setCheckable(True)
        enable_notes_act.setChecked(bool(self.settings.get('behavior.enable_sticky_notes', True)))
        enable_notes_act.toggled.connect(lambda enabled: self.settings.set('behavior.enable_sticky_notes', enabled))
        new_note_act = notes_menu.addAction('➕ Add Sticky Note')
        new_note_act.triggered.connect(lambda: self.create_desktop_sticky_note(global_pos))
        toggle_notes_act = notes_menu.addAction('🕸️ Show / Hide Desktop Notes')
        toggle_notes_act.triggered.connect(lambda: self.toggle_desktop_sticky_notes())
        dashboard_notes_act = notes_menu.addAction('📋 Open Notes Dashboard')
        dashboard_notes_act.triggered.connect(lambda: self.open_sticky_notes_dashboard())

        if hasattr(self.behavior, "set_pinned") and getattr(self.behavior, "_is_pinned", False):
            unpin_act = menu.addAction('📌 Unpin Companion (Resume activities)')
            unpin_act.triggered.connect(lambda: self.behavior.set_pinned(False))
        menu.addSeparator()
        char_menu = menu.addMenu('Change Character')
        for char_id, profile in self.character_mgr.available_characters.items():
            action = char_menu.addAction(profile.display_name)
            action.setCheckable(True)
            action.setChecked(bool(self.character_mgr.active_character and self.character_mgr.active_character.id == char_id))
            action.triggered.connect(lambda checked=False, cid=char_id: self.character_mgr.set_active_character(cid))
        mode_menu = menu.addMenu('Change Display Mode')
        for label, value in [('Entire Desktop', 'desktop'), ('Selected Applications', 'application')]:
            action = mode_menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(self.settings.get('general.display_mode') == value)
            action.triggered.connect(lambda checked=False, value=value: self.settings.set('general.display_mode', value))
        size_menu = menu.addMenu('Character Size')
        for label, height in [('Small', 120), ('Medium', 200), ('Large', 300)]:
            action = size_menu.addAction(label)
            action.triggered.connect(lambda checked=False, height=height: self.settings.set('general.scale', height/200))
        fx_menu = menu.addMenu('⚡ Interactive FX')
        fling_act = fx_menu.addAction('🚀 Drag-and-Throw (Fling Physics)')
        fling_act.setCheckable(True)
        fling_act.setChecked(bool(self.settings.get('behavior.enable_fling_physics', True)))
        fling_act.toggled.connect(lambda enabled: self.settings.set('behavior.enable_fling_physics', enabled))

        web_cursor_act = fx_menu.addAction('🕸️ Web-Shoot to Cursor (Ctrl+Click)')
        web_cursor_act.setCheckable(True)
        web_cursor_act.setChecked(bool(self.settings.get('behavior.enable_web_shoot_cursor', True)))
        web_cursor_act.toggled.connect(lambda enabled: self.settings.set('behavior.enable_web_shoot_cursor', enabled))

        follow_act = fx_menu.addAction('🎯 Mouse Chase / Follow Mode')
        follow_act.setCheckable(True)
        follow_act.setChecked(bool(self.settings.get('behavior.enable_mouse_following', True)))
        follow_act.toggled.connect(lambda enabled: self.settings.set('behavior.enable_mouse_following', enabled))

        dodge_act = fx_menu.addAction('⚡ Spider-Sense Dodging')
        dodge_act.setCheckable(True)
        dodge_act.setChecked(bool(self.settings.get('behavior.enable_spider_sense_dodging', True)))
        dodge_act.toggled.connect(lambda enabled: self.settings.set('behavior.enable_spider_sense_dodging', enabled))

        bubble_act = fx_menu.addAction('💬 Comic Speech Bubbles')
        bubble_act.setCheckable(True)
        bubble_act.setChecked(bool(self.settings.get('behavior.enable_comic_bubbles', True)))
        bubble_act.toggled.connect(lambda enabled: self.settings.set('behavior.enable_comic_bubbles', enabled))

        hotkey_act = fx_menu.addAction('⌨️ Quick Animation Keys (1..0)')
        hotkey_act.setCheckable(True)
        hotkey_act.setChecked(bool(self.settings.get('behavior.enable_animation_hotkeys', True)))
        hotkey_act.toggled.connect(lambda enabled: self.settings.set('behavior.enable_animation_hotkeys', enabled))

        sound_menu = menu.addMenu('Sound')
        sound = sound_menu.addAction('Enable sounds')
        sound.setCheckable(True)
        sound.setChecked(bool(self.settings.get('behavior.sound_enabled', False)))
        sound.toggled.connect(lambda enabled: self.settings.set('behavior.sound_enabled', enabled))
        sound_menu.addAction('Volume').setEnabled(False)
        volume = QSlider(Qt.Horizontal)
        volume.setRange(0, 100)
        volume.setValue(round(float(self.settings.get('behavior.sound_volume', .25))*100))
        volume.valueChanged.connect(lambda value: self.settings.set('behavior.sound_volume', value/100))
        volume_action = QWidgetAction(sound_menu)
        volume_action.setDefaultWidget(volume)
        sound_menu.addAction(volume_action)
        menu.addAction('Settings', self.open_dashboard_requested.emit)
        menu.addSeparator()
        menu.addAction('Exit', self.quit_requested.emit)
        self._menu_open = self.behavior.cursor_attention = True
        try:
            menu.exec(global_pos)
        finally:
            self._menu_open = self.behavior.cursor_attention = False
            self.behavior.resume_autonomy()
            menu.deleteLater()
