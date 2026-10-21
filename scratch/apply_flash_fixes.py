"""Script to surgically apply screen flicker and DWM flashing fixes."""
import re
from pathlib import Path

# 1. Fix overlay/transparent_overlay.py
p1 = Path("overlay/transparent_overlay.py")
content = p1.read_text(encoding="utf-8")

# Remove clearMask in set_battery_charging
old_charging = """        if self._is_charging:
            if self._character_id != "miles_morales" and not self._charging_timer.isActive():
                self._stark_optics_flash = 5
            self.clearMask()
            if not self._charging_timer.isActive():
                self._charging_timer.start()"""

new_charging = """        if self._is_charging:
            if self._character_id != "miles_morales" and not self._charging_timer.isActive():
                self._stark_optics_flash = 5
            if not self._charging_timer.isActive():
                self._charging_timer.start()"""

assert old_charging in content, "Failed to find old_charging in transparent_overlay.py"
content = content.replace(old_charging, new_charging)

# Remove clearMask in trigger_suit_glitch
old_glitch = """        self._glitch_active = True
        self._glitch_frame = 0
        self.clearMask()
        if not self._glitch_timer.isActive():"""

new_glitch = """        self._glitch_active = True
        self._glitch_frame = 0
        if not self._glitch_timer.isActive():"""

assert old_glitch in content, "Failed to find old_glitch in transparent_overlay.py"
content = content.replace(old_glitch, new_glitch)

# Remove clearMask in set_heavy_load
old_heavy = """        if self._is_heavy_load:
            self.clearMask()
        elif not self._is_music_playing and not self._glitch_active:
            self._apply_input_region()"""

new_heavy = """        if not self._is_heavy_load and not self._is_music_playing and not self._glitch_active:
            self._apply_input_region()"""

assert old_heavy in content, "Failed to find old_heavy in transparent_overlay.py"
content = content.replace(old_heavy, new_heavy)

# Remove clearMask in set_music_playing
old_music = """        if self._is_music_playing:
            self.clearMask()
            if not self._audio_anim_timer.isActive():
                self._audio_anim_timer.start()"""

new_music = """        if self._is_music_playing:
            if not self._audio_anim_timer.isActive():
                self._audio_anim_timer.start()"""

assert old_music in content, "Failed to find old_music in transparent_overlay.py"
content = content.replace(old_music, new_music)

# Remove clearMask in _apply_input_region
old_input = """    def _apply_input_region(self):
        # Translucent click-through hit testing is handled natively via WM_NCHITTEST
        # in nativeEvent() returning HTTRANSPARENT (-1) for transparent pixels.
        # Calling SetWindowRgn/setMask at 10-60 FPS destroys Windows DWM swapchain sync,
        # which causes monitor sync drops, screen flashing, and UI redraw glitches.
        if self._last_applied_mask is not None:
            self.clearMask()
            self._last_applied_mask = None"""

new_input = """    def _apply_input_region(self):
        # Translucent click-through hit testing is handled natively via WM_NCHITTEST
        # in nativeEvent() returning HTTRANSPARENT (-1) for transparent pixels.
        # Calling SetWindowRgn/setMask at 10-60 FPS destroys Windows DWM swapchain sync,
        # which causes monitor sync drops, screen flashing, and UI redraw glitches.
        self._last_applied_mask = None"""

assert old_input in content, "Failed to find old_input in transparent_overlay.py"
content = content.replace(old_input, new_input)

p1.write_text(content, encoding="utf-8")
print("Successfully patched overlay/transparent_overlay.py")

# 2. Fix overlay/comic_effects_overlay.py
p2 = Path("overlay/comic_effects_overlay.py")
c2 = p2.read_text(encoding="utf-8")

old_init2 = """        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.NoFocus)"""

new_init2 = """        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.NoFocus)"""

assert old_init2 in c2, "Failed to find old_init2 in comic_effects_overlay.py"
c2 = c2.replace(old_init2, new_init2)

# Prevent redundant move() calls in _update_geometry
old_move2 = """        self.move(target_x, target_y)"""
new_move2 = """        if self.pos() != QPoint(target_x, target_y):
            self.move(target_x, target_y)"""
assert old_move2 in c2, "Failed to find old_move2 in comic_effects_overlay.py"
c2 = c2.replace(old_move2, new_move2)

# Clear transparent in paintEvent
old_paint2 = """    def paintEvent(self, event):
        has_active = (
            self._spider_sense_active
            or self._bubble_active
            or self._heavy_load_active
            or self._music_active
            or self._charging_active
            or bool(self._soundwave_rings)
            or bool(self._music_notes)
        )
        if not has_active:
            return

        now = time.monotonic()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)"""

new_paint2 = """    def nativeEvent(self, event_type, message):
        import sys
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == 0x0014:  # WM_ERASEBKGND
                return True, 1
            if msg.message == 0x0021:  # WM_MOUSEACTIVATE / MA_NOACTIVATE
                return True, 3
        return super().nativeEvent(event_type, message)

    def paintEvent(self, event):
        has_active = (
            self._spider_sense_active
            or self._bubble_active
            or self._heavy_load_active
            or self._music_active
            or self._charging_active
            or bool(self._soundwave_rings)
            or bool(self._music_notes)
        )
        painter = QPainter(self)
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        painter.fillRect(self.rect(), Qt.transparent)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        if not has_active:
            painter.end()
            return

        now = time.monotonic()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)"""

assert old_paint2 in c2, "Failed to find old_paint2 in comic_effects_overlay.py"
c2 = c2.replace(old_paint2, new_paint2)

p2.write_text(c2, encoding="utf-8")
print("Successfully patched overlay/comic_effects_overlay.py")

# 3. Fix overlay/web_overlay.py
p3 = Path("overlay/web_overlay.py")
c3 = p3.read_text(encoding="utf-8")

old_init3 = """        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.NoFocus)"""

new_init3 = """        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.NoFocus)"""

assert old_init3 in c3, "Failed to find old_init3 in web_overlay.py"
c3 = c3.replace(old_init3, new_init3)

old_paint3 = """    def paintEvent(self, event):
        if not self.points:
            return
        painter = QPainter(self)"""

new_paint3 = """    def nativeEvent(self, event_type, message):
        import sys
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == 0x0014:  # WM_ERASEBKGND
                return True, 1
            if msg.message == 0x0021:  # WM_MOUSEACTIVATE / MA_NOACTIVATE
                return True, 3
        return super().nativeEvent(event_type, message)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        painter.fillRect(self.rect(), Qt.transparent)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        if not self.points:
            painter.end()
            return"""

assert old_paint3 in c3, "Failed to find old_paint3 in web_overlay.py"
c3 = c3.replace(old_paint3, new_paint3)

p3.write_text(c3, encoding="utf-8")
print("Successfully patched overlay/web_overlay.py")

# 4. Fix overlay/corner_web_overlay.py
p4 = Path("overlay/corner_web_overlay.py")
c4 = p4.read_text(encoding="utf-8")

old_init4 = """        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.NoFocus)"""

new_init4 = """        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.NoFocus)"""

assert old_init4 in c4, "Failed to find old_init4 in corner_web_overlay.py"
c4 = c4.replace(old_init4, new_init4)

old_paint4 = """        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        painter.setOpacity(opacity)"""

new_paint4 = """    def nativeEvent(self, event_type, message):
        import sys
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == 0x0014:  # WM_ERASEBKGND
                return True, 1
            if msg.message == 0x0021:  # WM_MOUSEACTIVATE / MA_NOACTIVATE
                return True, 3
        return super().nativeEvent(event_type, message)

        painter = QPainter(self)
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        painter.fillRect(self.rect(), Qt.transparent)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        painter.setOpacity(opacity)"""

# Wait, let's place nativeEvent before paintEvent in corner_web_overlay
assert old_paint4 in c4, "Failed to find old_paint4 in corner_web_overlay.py"
# Let's find def paintEvent in c4
old_def_paint4 = """    def paintEvent(self, event) -> None:
        if not self._active:
            return"""

new_def_paint4 = """    def nativeEvent(self, event_type, message):
        import sys
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == 0x0014:  # WM_ERASEBKGND
                return True, 1
            if msg.message == 0x0021:  # WM_MOUSEACTIVATE / MA_NOACTIVATE
                return True, 3
        return super().nativeEvent(event_type, message)

    def paintEvent(self, event) -> None:
        if not self._active:
            return"""

assert old_def_paint4 in c4, "Failed to find old_def_paint4 in corner_web_overlay.py"
c4 = c4.replace(old_def_paint4, new_def_paint4)

old_painter_start4 = """        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)"""
new_painter_start4 = """        painter = QPainter(self)
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        painter.fillRect(self.rect(), Qt.transparent)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        painter.setRenderHint(QPainter.Antialiasing)"""
assert old_painter_start4 in c4, "Failed to find old_painter_start4 in corner_web_overlay.py"
c4 = c4.replace(old_painter_start4, new_painter_start4)

p4.write_text(c4, encoding="utf-8")
print("Successfully patched overlay/corner_web_overlay.py")

# 5. Fix overlay/trampoline_overlay.py
p5 = Path("overlay/trampoline_overlay.py")
c5 = p5.read_text(encoding="utf-8")

old_init5 = """        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.NoFocus)"""

new_init5 = """        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.NoFocus)"""

assert old_init5 in c5, "Failed to find old_init5 in trampoline_overlay.py"
c5 = c5.replace(old_init5, new_init5)

old_paint5 = """    def paintEvent(self, event) -> None:
        if not self._is_active:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)"""

new_paint5 = """    def nativeEvent(self, event_type, message):
        import sys
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == 0x0014:  # WM_ERASEBKGND
                return True, 1
            if msg.message == 0x0021:  # WM_MOUSEACTIVATE / MA_NOACTIVATE
                return True, 3
        return super().nativeEvent(event_type, message)

    def paintEvent(self, event) -> None:
        if not self._is_active:
            return

        painter = QPainter(self)
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        painter.fillRect(self.rect(), Qt.transparent)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        painter.setRenderHint(QPainter.Antialiasing)"""

assert old_paint5 in c5, "Failed to find old_paint5 in trampoline_overlay.py"
c5 = c5.replace(old_paint5, new_paint5)

p5.write_text(c5, encoding="utf-8")
print("Successfully patched overlay/trampoline_overlay.py")

# 6. Fix ui/web_window.py
p6 = Path("ui/web_window.py")
c6 = p6.read_text(encoding="utf-8")

old_close6 = """    def closeEvent(self, event):
        \"\"\"Ensure web server stops cleanly when window is closed.\"\"\""""

new_close6 = """    def nativeEvent(self, event_type, message):
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == 0x0014:  # WM_ERASEBKGND: prevent white GDI flash before Chromium paints
                return True, 1
        return super().nativeEvent(event_type, message)

    def closeEvent(self, event):
        \"\"\"Ensure web server stops cleanly when window is closed.\"\"\""""

assert old_close6 in c6, "Failed to find old_close6 in web_window.py"
c6 = c6.replace(old_close6, new_close6)

p6.write_text(c6, encoding="utf-8")
print("Successfully patched ui/web_window.py")
print("ALL PATCHES APPLIED SUCCESSFULLY!")
