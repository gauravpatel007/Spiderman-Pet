"""Apply permanent anti-flicker, ground-positioning, and title-hang fixes."""
import re
from pathlib import Path

root = Path(__file__).resolve().parent.parent

# 1. Fix app/bootstrap.py: Remove harmful Chromium flags (--disable-direct-composition, --enable-begin-frame-scheduling)
bootstrap_path = root / "app" / "bootstrap.py"
content = bootstrap_path.read_text(encoding="utf-8")
old_flags_pattern = r'flags_to_add = \(\s*"--use-angle=d3d11 ".*?\)'
new_flags = '''flags_to_add = (
        "--use-angle=d3d11 "
        "--disable-features=CalculateNativeWinOcclusion,WindowOcclusionCalculation,MrcMultiplaneOverlay "
        "--disable-backgrounding-occluded-windows"
    )'''
content = re.sub(old_flags_pattern, new_flags, content, flags=re.DOTALL)
bootstrap_path.write_text(content, encoding="utf-8")
print("1. Updated app/bootstrap.py")

# 2. Fix overlay/transparent_overlay.py:
trans_path = root / "overlay" / "transparent_overlay.py"
trans_code = trans_path.read_text(encoding="utf-8")
trans_code = re.sub(r'^\s*self\.setAttribute\(Qt\.WA_NoSystemBackground\)\s*$', '', trans_code, flags=re.MULTILINE)
trans_code = re.sub(
    r'def paintEvent\(self, event\):\s+painter = QPainter\(self\)\s+painter\.setCompositionMode\(QPainter\.CompositionMode_Source\)\s+painter\.fillRect\(self\.rect\(\), Qt\.transparent\)\s+painter\.setCompositionMode\(QPainter\.CompositionMode_SourceOver\)',
    'def paintEvent(self, event):\n        painter = QPainter(self)',
    trans_code
)
trans_path.write_text(trans_code, encoding="utf-8")
print("2. Updated overlay/transparent_overlay.py")

# 3. Fix secondary overlays:
for ov_name in ["comic_effects_overlay.py", "corner_web_overlay.py", "trampoline_overlay.py", "web_overlay.py"]:
    ov_path = root / "overlay" / ov_name
    if not ov_path.exists():
        continue
    c = ov_path.read_text(encoding="utf-8")
    c = re.sub(r'^\s*self\.setAttribute\(Qt\.WA_NoSystemBackground\)\s*$', '', c, flags=re.MULTILINE)
    c = re.sub(
        r'painter\.setCompositionMode\(QPainter\.CompositionMode_Source\)\s+painter\.fillRect\(self\.rect\(\), Qt\.transparent\)\s+painter\.setCompositionMode\(QPainter\.CompositionMode_SourceOver\)\s*',
        '',
        c
    )
    ov_path.write_text(c, encoding="utf-8")
    print(f"3. Updated overlay/{ov_name}")

# 4. Fix overlay/overlay_manager.py: Ensure default_position firmly on ground floor when choice == 'bottom_right'
om_path = root / "overlay" / "overlay_manager.py"
om_code = om_path.read_text(encoding="utf-8")
old_def_pos_pat = r'def default_position\(self, area\):.*?return area\.x\(\)\+x, area\.y\(\)\+height'
new_def_pos = '''def default_position(self, area):
        choice = self.settings.get('general.default_position', 'bottom_right')
        width = max(0, area.width() - self.movement.width)
        height = max(0, area.height() - self.movement.height)
        if choice == 'bottom_right':
            return area.x() + max(0, width - 16), area.y() + height
        if choice == 'bottom_left':
            return area.x() + min(16, width), area.y() + height
        if choice == 'custom':
            last_pos = self.settings.get('general.last_position')
            if last_pos and isinstance(last_pos, (list, tuple)) and len(last_pos) >= 2:
                lx, ly = float(last_pos[0]), float(last_pos[1])
                px = max(area.x(), min(lx, area.x() + max(0, area.width() - self.movement.width)))
                py = max(area.y(), min(ly, area.y() + max(0, area.height() - self.movement.height)))
                return px, py
            fx, fy = self.settings.get('general.custom_position', [.1, .9])
            return area.x() + max(0, min(1, float(fx))) * width, area.y() + max(0, min(1, float(fy))) * height
        x = max(0, width - 16) if choice == 'bottom_right' else min(16, width)
        return area.x() + x, area.y() + height'''
om_code = re.sub(old_def_pos_pat, new_def_pos, om_code, flags=re.DOTALL)
om_path.write_text(om_code, encoding="utf-8")
print("4. Updated overlay/overlay_manager.py")

# 5. Fix core/behavior_controller.py: Exclude docked/perched/climbing states from _on_airborne
bc_path = root / "core" / "behavior_controller.py"
bc_code = bc_path.read_text(encoding="utf-8")
old_air_pat = r'def _on_airborne\(self\):.*?self\.state_machine\.transition_to\(CharacterState\.FALL, force=True\)'
new_air = '''def _on_airborne(self):
        if getattr(self, "_is_pinned", False):
            return
        if self.state_machine.current_state not in (
            CharacterState.DRAGGED,
            CharacterState.FALL,
            CharacterState.TITLE_PERCH,
            CharacterState.TITLE_HANG,
            CharacterState.HANG,
            CharacterState.PERCH,
            CharacterState.CLIMB_UP,
            CharacterState.CLIMB_DOWN,
            CharacterState.FOCUS_READ,
        ):
            self.state_machine.transition_to(CharacterState.FALL, force=True)'''
bc_code = re.sub(old_air_pat, new_air, bc_code, flags=re.DOTALL)
bc_path.write_text(bc_code, encoding="utf-8")
print("5. Updated core/behavior_controller.py")

# 6. Fix core/interaction_manager.py: Ground sit posture docking & dragging
im_path = root / "core" / "interaction_manager.py"
im_code = im_path.read_text(encoding="utf-8")
old_rel_fall_pat = r'else:\s+self\.state_machine\.transition_to\(C\.LAND if self\.movement\.is_grounded else C\.FALL, force=True\)'
new_rel_fall = '''else:
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
                    self.state_machine.transition_to(C.LAND if self.movement.is_grounded else C.FALL, force=True)'''
im_code = re.sub(old_rel_fall_pat, new_rel_fall, im_code)
im_path.write_text(im_code, encoding="utf-8")
print("6. Updated core/interaction_manager.py")
print("All permanent fixes applied cleanly via regex!")
