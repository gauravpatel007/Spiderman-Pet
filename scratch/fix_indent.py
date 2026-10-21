from pathlib import Path
p = Path("core/interaction_manager.py")
text = p.read_text(encoding="utf-8")

# Find the duplicate else block
bad_block = """            else:
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
                    self.state_machine.transition_to(C.LAND if self.movement.is_grounded else C.FALL, force=True)"""

good_block = """            else:
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
                    self.state_machine.transition_to(C.LAND if self.movement.is_grounded else C.FALL, force=True)"""

text = text.replace(bad_block.replace("\r\n", "\n"), good_block.replace("\r\n", "\n"))
p.write_text(text, encoding="utf-8")
print("Cleaned up interaction_manager.py successfully!")
