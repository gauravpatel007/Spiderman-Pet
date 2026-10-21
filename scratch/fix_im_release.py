from pathlib import Path
p = Path("core/interaction_manager.py")
text = p.read_text(encoding="utf-8")

old = """        if self._is_ground_sit_drag:
            self._is_ground_sit_drag = False
            self._is_dragging = self.movement.is_dragging = False

            press_pos = self._ground_sit_press_pos or QPoint(int(self.movement.x), int(self.movement.y))
            cursor_pos = QCursor.pos() if hasattr(QCursor, 'pos') else press_pos
            dx = cursor_pos.x() - press_pos.x()
            dy = cursor_pos.y() - press_pos.y()

            if dy < -65 and abs(dy) > 1.6 * abs(dx):
                # Detached upward into jump!
                self.movement.set_motion("jump", 0.0, -180.0)
                self.state_machine.transition_to(C.JUMP, force=True)
                return True

            # Settle firmly on the ground in SIT posture!
            active_area = self.movement.active_region() or (self.movement.regions[0] if self.movement.regions else None)
            if active_area is not None:
                ground_y = active_area.bottom() - self.movement.height + 1
                self.movement.set_position(self.movement.x, ground_y)
            self.state_machine.transition_to(C.SIT, force=True)
            if hasattr(self.behavior, "set_pinned"):
                self.behavior.set_pinned(True, keep_state=True)
            if self.overlay and hasattr(self.overlay, "show_speech_bubble"):
                self.overlay.show_speech_bubble("Chilling right here! 😎", 1600, "comic")
            return True"""

new = """        if self._is_ground_sit_drag:
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
            return True"""

text = text.replace(old.replace("\r\n", "\n"), new.replace("\r\n", "\n"))
p.write_text(text, encoding="utf-8")
print("Updated interaction_manager.py ground sit drag release successfully!")
