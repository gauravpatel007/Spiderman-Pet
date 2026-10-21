"""Apply --use-angle=d3d11 and position change throttling."""
from pathlib import Path

# 1. Update app/bootstrap.py
p1 = Path("app/bootstrap.py")
c1 = p1.read_text(encoding="utf-8")

old_bootstrap = """    flags_to_add = (
        "--disable-direct-composition "
        "--disable-direct-composition-video-overlays "
        "--disable-features=CalculateNativeWinOcclusion,WindowOcclusionCalculation,MrcMultiplaneOverlay "
        "--disable-backgrounding-occluded-windows "
        "--enable-begin-frame-scheduling"
    )
    if "--disable-direct-composition" not in existing_flags:
        os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = f"{existing_flags} {flags_to_add}".strip()"""

new_bootstrap = """    flags_to_add = (
        "--use-angle=d3d11 "
        "--disable-direct-composition "
        "--disable-direct-composition-video-overlays "
        "--disable-features=CalculateNativeWinOcclusion,WindowOcclusionCalculation,MrcMultiplaneOverlay "
        "--disable-backgrounding-occluded-windows "
        "--enable-begin-frame-scheduling"
    )
    if "--use-angle=d3d11" not in existing_flags:
        os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = f"{existing_flags} {flags_to_add}".strip()"""

assert old_bootstrap in c1, "old_bootstrap not found"
c1 = c1.replace(old_bootstrap, new_bootstrap)
p1.write_text(c1, encoding="utf-8")
print("Patched app/bootstrap.py")

# 2. Update overlay/transparent_overlay.py
p2 = Path("overlay/transparent_overlay.py")
c2 = p2.read_text(encoding="utf-8")

old_pos = """    def update_position(self, x: int, y: int):
        self.move(int(x), int(y))"""

new_pos = """    def update_position(self, x: int, y: int):
        target = QPoint(int(x), int(y))
        if self.pos() != target:
            self.move(target)"""

assert old_pos in c2, "old_pos not found in transparent_overlay.py"
c2 = c2.replace(old_pos, new_pos)
p2.write_text(c2, encoding="utf-8")
print("Patched overlay/transparent_overlay.py")

# 3. Update core/movement_controller.py
p3 = Path("core/movement_controller.py")
c3 = p3.read_text(encoding="utf-8")

old_move = """        self.position_changed.emit(round(self.x), round(self.y))"""
new_move = """        rx, ry = round(self.x), round(self.y)
        if getattr(self, '_last_emitted_pos', None) != (rx, ry):
            self._last_emitted_pos = (rx, ry)
            self.position_changed.emit(rx, ry)"""

assert old_move in c3, "old_move not found in movement_controller.py"
c3 = c3.replace(old_move, new_move)
p3.write_text(c3, encoding="utf-8")
print("Patched core/movement_controller.py")
print("All hardware and throttling patches applied!")
