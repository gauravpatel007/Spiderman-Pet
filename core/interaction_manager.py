"""Local cursor observation, bounded dragging and character controls."""
import math
import random
import time
from PySide6.QtCore import QObject, QPoint, Signal, Qt, QTimer
from PySide6.QtGui import QCursor, QGuiApplication
from PySide6.QtWidgets import QMenu, QWidgetAction, QSlider
from services.settings_service import get_settings
from .state_machine import CharacterState, CharacterState as C


def is_shift_pressed() -> bool:
    """Detect if Shift key is physically pressed in real-time, even when window lacks focus."""
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
        if (user32.GetKeyState(0x10) & 0x8000) != 0:
            return True
    except Exception:
        pass
    try:
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtCore import Qt
        if bool(QGuiApplication.keyboardModifiers() & Qt.ShiftModifier):
            return True
    except Exception:
        pass
    return False


class InteractionManager(QObject):
    open_dashboard_requested = Signal()
    quit_requested = Signal()

    def __init__(self, state_machine, movement, character_mgr, animation=None, behavior=None, parent=None):
        super().__init__(parent)
        self.state_machine, self.movement, self.character_mgr = state_machine, movement, character_mgr
        self.animation, self.behavior = animation, behavior
        self.settings = get_settings()
        self.overlay = None
        self._is_dragging = False
        self._shift_drag = False
        self._drag_offset = QPoint()
        self._last_cursor = None
        self._last_sample = time.monotonic()
        self._last_reaction = 0.0
        self._last_dodge_time = 0.0
        self._nearby = self._menu_open = False
        self._cursor_timer = QTimer(self)
        self._cursor_timer.setInterval(75)
        self._cursor_timer.timeout.connect(self._track_cursor)

    def start(self):
        self._last_cursor = None
        self._cursor_timer.start()

    def stop(self):
        self._cursor_timer.stop()
        self._last_cursor = None
        self._nearby = False
        self.behavior.cursor_attention = False

    def handle_mouse_press(self, global_pos, local_pos, button):
        if button != Qt.LeftButton:
            return False
        is_shift = is_shift_pressed()
        self._shift_drag = is_shift
        # If user moves him normally without Shift, unpin him!
        if not is_shift and hasattr(self.behavior, "set_pinned") and getattr(self.behavior, "_is_pinned", False):
            self.behavior.set_pinned(False)

        self.behavior.user_override()
        self._is_dragging = self.movement.is_dragging = True
        self._drag_offset = local_pos
        self.state_machine.transition_to(C.DRAGGED, force=True)
        return True

    def handle_mouse_move(self, global_pos):
        if not self._is_dragging:
            return False
        if is_shift_pressed():
            self._shift_drag = True
        self.movement.set_position(global_pos.x()-self._drag_offset.x(), global_pos.y()-self._drag_offset.y())
        return True

    def handle_mouse_release(self, button):
        if button != Qt.LeftButton or not self._is_dragging:
            return False
        self._is_dragging = self.movement.is_dragging = False

        is_shift = is_shift_pressed() or self._shift_drag
        if is_shift and hasattr(self.behavior, "set_pinned"):
            # Shift+drag: lock in place, no activities, hold position!
            self.behavior.set_pinned(True)
        else:
            self.state_machine.transition_to(C.LAND if self.movement.is_grounded else C.FALL, force=True)

        self._shift_drag = False
        return True

    def play_activity(self, state: CharacterState):
        """Immediately test or play an activity on Spider-Man."""
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
        if not is_override and not self.behavior.activity_enabled(state):
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
        """Phase 10.3: Shoot a visible web line toward the given point."""
        hand_x = self.movement.x + (self.movement.width * (0.25 if self.movement.is_facing_left else 0.75))
        hand_y = self.movement.y + self.movement.height * 0.4
        strand = ((hand_x, hand_y), (float(target_pos.x()), float(target_pos.y())))
        self.movement.web_changed.emit(strand)
        QTimer.singleShot(450, lambda: self.movement.web_changed.emit(None))
        self._request(C.WAVE)
        if self.overlay and hasattr(self.overlay, "show_speech_bubble"):
            self.overlay.show_speech_bubble("THWIP!", 1400, "action")

    def _track_cursor(self):
        if (
            self._is_dragging
            or self._menu_open
            or not self.overlay
            or not self.overlay.isVisible()
            or not self.settings.get('behavior.enable_mouse_following', True)
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
            and self.state_machine.current_state not in (C.DRAGGED, C.SLEEP)
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

        # Normal cursor tracking / following
        inside = any(region.contains(point) for region in self.movement.regions)
        radius = max(30, float(self.settings.get('behavior.cursor_radius', 180)))
        nearby = (inside and (point-center).manhattanLength() < radius
                  and self.behavior._idle_seconds < float(self.settings.get('behavior.inactivity.relax_seconds', 120)))
        safe = self.state_machine.current_state in (C.IDLE, C.WALK, C.RUN, C.SIT, C.WAVE)
        if nearby and safe:
            if not self._nearby and self.state_machine.current_state in (C.WALK, C.RUN):
                self.state_machine.transition_to(C.IDLE, force=True)
            facing = point.x() < center.x()
            self.movement.is_facing_left = facing
            self.animation.set_facing_left(facing)
            if cursor_speed > 1000 and now-self._last_reaction > 12 and random.random() < .2:
                self._last_reaction = now
                self._request(C.WAVE)
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
        web_act = menu.addAction('🕸️ Shoot Web')
        web_act.triggered.connect(lambda: self.shoot_web_at(global_pos))
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
        dodge_act = fx_menu.addAction('⚡ Spider-Sense Dodging')
        dodge_act.setCheckable(True)
        dodge_act.setChecked(bool(self.settings.get('behavior.enable_spider_sense_dodging', True)))
        dodge_act.toggled.connect(lambda enabled: self.settings.set('behavior.enable_spider_sense_dodging', enabled))

        bubble_act = fx_menu.addAction('💬 Comic Speech Bubbles')
        bubble_act.setCheckable(True)
        bubble_act.setChecked(bool(self.settings.get('behavior.enable_comic_bubbles', True)))
        bubble_act.toggled.connect(lambda enabled: self.settings.set('behavior.enable_comic_bubbles', enabled))

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
