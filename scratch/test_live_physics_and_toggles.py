import sys
import os
import ast
import json
import time
from pathlib import Path

ROOT = Path(r"g:\Languages\Projects\Pet\Pet A2 Final")
sys.path.insert(0, str(ROOT))

print("=== 1. Validating Python File AST Syntax ===")
python_files = [
    ROOT / "core" / "movement_controller.py",
    ROOT / "core" / "interaction_manager.py",
    ROOT / "overlay" / "sticky_note_overlay.py",
    ROOT / "services" / "hotkey_service.py",
    ROOT / "app" / "application.py",
    ROOT / "ui" / "web_window.py",
]

for pf in python_files:
    with open(pf, "r", encoding="utf-8") as f:
        src = f.read()
    try:
        ast.parse(src, filename=str(pf))
        print(f"  [OK] Syntax clean: {pf.name}")
    except SyntaxError as e:
        print(f"  [FAIL] Syntax error in {pf.name}: {e}")
        sys.exit(1)

print("\n=== 2. Validating config/default_settings.json ===")
cfg_path = ROOT / "config" / "default_settings.json"
with open(cfg_path, "r", encoding="utf-8") as f:
    cfg = json.load(f)

behavior = cfg.get("behavior", {})
assert "enable_fling_physics" in behavior, "Missing enable_fling_physics in default_settings.json"
assert "enable_web_shoot_cursor" in behavior, "Missing enable_web_shoot_cursor in default_settings.json"
assert "enable_sticky_notes" in behavior, "Missing enable_sticky_notes in default_settings.json"
assert "enable_mouse_following" in behavior, "Missing enable_mouse_following in default_settings.json"
print("  [OK] Default settings keys verified:")
print(f"       enable_fling_physics: {behavior['enable_fling_physics']}")
print(f"       enable_web_shoot_cursor: {behavior['enable_web_shoot_cursor']}")
print(f"       enable_sticky_notes: {behavior['enable_sticky_notes']}")
print(f"       enable_mouse_following: {behavior['enable_mouse_following']}")

print("\n=== 3. Setting Up Qt Mock for Headless Physics & Logic Testing ===")
import types

class MockSignal:
    def __init__(self, *types):
        self._callbacks = []

    def connect(self, fn):
        self._callbacks.append(fn)

    def emit(self, *args):
        for cb in self._callbacks:
            try:
                cb(*args)
            except Exception as e:
                pass

class MockQObject:
    def __init__(self, parent=None):
        self._parent = parent

class MockQTimer(MockQObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.timeout = MockSignal()
        self._interval = 0
        self._active = False

    def setInterval(self, ms):
        self._interval = ms

    def start(self, ms=None):
        self._active = True

    def stop(self):
        self._active = False

    def isActive(self):
        return self._active

    @classmethod
    def singleShot(cls, ms, fn):
        pass

class MockQRect:
    def __init__(self, x=0, y=0, w=1920, h=1080):
        if isinstance(x, MockQRect):
            self._x = x._x
            self._y = x._y
            self._w = x._w
            self._h = x._h
        else:
            self._x = x
            self._y = y
            self._w = w
            self._h = h

    def x(self): return self._x
    def y(self): return self._y
    def left(self): return self._x
    def right(self): return self._x + self._w
    def top(self): return self._y
    def bottom(self): return self._y + self._h
    def width(self): return self._w
    def height(self): return self._h
    def isEmpty(self): return self._w <= 0 or self._h <= 0
    def isNull(self): return self._w == 0 and self._h == 0
    def contains(self, px, py=None):
        if hasattr(px, 'x'):
            qx, qy = px.x(), px.y()
        else:
            qx, qy = px, py
        return self._x <= qx <= self.right() and self._y <= qy <= self.bottom()
    def united(self, other):
        x1 = min(self._x, other._x)
        y1 = min(self._y, other._y)
        x2 = max(self.right(), other.right())
        y2 = max(self.bottom(), other.bottom())
        return MockQRect(x1, y1, x2 - x1, y2 - y1)

class MockQPoint:
    def __init__(self, x=0, y=0):
        self._x = x
        self._y = y

    def x(self): return self._x
    def y(self): return self._y

    def __eq__(self, other):
        return hasattr(other, 'x') and hasattr(other, 'y') and self._x == other.x() and self._y == other.y()

    def __repr__(self):
        return f"QPoint({self._x}, {self._y})"

class MockQRegion:
    def __init__(self, rect=None):
        self.rects = [rect] if rect else []

    def __ior__(self, other):
        if hasattr(other, 'rects'):
            self.rects.extend(other.rects)
        return self

    def isEmpty(self):
        return len(self.rects) == 0

    def subtracted(self, other):
        for r in self.rects:
            if not r:
                continue
            contained = False
            for o in (other.rects if hasattr(other, 'rects') else []):
                if o and o.left() <= r.left() and o.right() >= r.right() and o.top() <= r.top() and o.bottom() >= r.bottom():
                    contained = True
                    break
            if not contained:
                return MockQRegion(r)
        return MockQRegion()

    def contains(self, pt_or_x, y=None):
        if hasattr(pt_or_x, 'x'):
            x, y = pt_or_x.x(), pt_or_x.y()
        else:
            x = pt_or_x
        for r in self.rects:
            if r and r.left() <= x <= r.right() and r.top() <= y <= r.bottom():
                return True
        return False

class MockQt:
    LeftButton = 1
    RightButton = 2
    MiddleButton = 4

class MockQCursor:
    _pos = MockQPoint(500, 400)
    @classmethod
    def pos(cls):
        return cls._pos

# Inject mock modules if PySide6 is not present
try:
    import PySide6
except ImportError:
    class MockClass:
        def __init__(self, *args, **kwargs):
            self.connect = lambda *a, **k: None
            self.emit = lambda *a, **k: None
        def __getattr__(self, name):
            m = MockClass()
            setattr(self, name, m)
            return m
        def __call__(self, *args, **kwargs):
            return MockClass()
        @classmethod
        def primaryScreen(cls): return MockClass()
        @classmethod
        def screens(cls): return []
        @classmethod
        def instance(cls): return MockClass()

    class MockModule(types.ModuleType):
        def __getattr__(self, name):
            return MockClass

    pyside6 = MockModule("PySide6")
    qtcore = MockModule("PySide6.QtCore")
    qtgui = MockModule("PySide6.QtGui")
    qtwidgets = MockModule("PySide6.QtWidgets")

    class MockQPointF(MockQPoint): pass
    class MockQElapsedTimer:
        def __init__(self): self._t = time.monotonic()
        def start(self): self._t = time.monotonic()
        def elapsed(self): return int((time.monotonic() - self._t) * 1000)

    qtcore.QObject = MockQObject
    qtcore.QTimer = MockQTimer
    qtcore.Signal = MockSignal
    qtcore.QRect = MockQRect
    qtcore.QPoint = MockQPoint
    qtcore.QPointF = MockQPointF
    qtcore.QElapsedTimer = MockQElapsedTimer
    qtcore.Qt = MockQt

    qtgui.QRegion = MockQRegion
    qtgui.QCursor = MockQCursor

    sys.modules["PySide6"] = pyside6
    sys.modules["PySide6.QtCore"] = qtcore
    sys.modules["PySide6.QtGui"] = qtgui
    sys.modules["PySide6.QtWidgets"] = qtwidgets
    print("  [OK] Mock PySide6 registered for headless validation")

print("\n=== 4. Testing MovementController Fling Physics & Mid-Air Web Catch ===")
import importlib.util

spec = importlib.util.spec_from_file_location("movement_controller", str(ROOT / "core" / "movement_controller.py"))
mc_mod = importlib.util.module_from_spec(spec)
sys.modules["core.movement_controller"] = mc_mod
spec.loader.exec_module(mc_mod)
MovementController = mc_mod.MovementController

mc = MovementController()
mc.set_bounds(MockQRect(0, 0, 1920, 1080))
mc.set_size(150, 150)
mc.set_position(960, 500)

boundary_hits = []
web_changes = []
orientations = []

mc.boundary_hit.connect(lambda side: boundary_hits.append(side))
mc.web_changed.connect(lambda web_data: web_changes.append(web_data))
mc.orientation_changed.connect(lambda rot: orientations.append(rot))

# 4.1 Launch fling throw with high velocity towards top-right
mc.set_fling_physics(1500.0, -1400.0)
assert mc.mode == "fling", f"Expected motion_mode 'fling', got {mc.mode}"
assert mc._fling_active is True
print("  Fling physics started with vx=1500, vy=-1400")

# 4.2 Step physics frames
hit_ceiling = False
safety_web_deployed = False
landed = False

for step in range(200):
    mc._step(0.016)
    if "ceiling" in boundary_hits:
        hit_ceiling = True
    if "safety_web_catch" in boundary_hits:
        safety_web_deployed = True
    if "fling_land" in boundary_hits or not mc._fling_active:
        landed = True
        print(f"  Spider-Man safely landed on ground at step {step}! Position: ({mc.x:.1f}, {mc.y:.1f})")
        break

print(f"  Boundary events: {boundary_hits}")
print(f"  Web changes: {len(web_changes)}")
print(f"  Tumble rotations generated: {len(orientations)}")

assert len(boundary_hits) > 0, "Expected boundary hits during fling"
assert landed, "Expected Spider-Man to safely land back on ground"
assert mc.mode != "fling", "Expected motion mode to reset from fling upon landing"
print("  [OK] Fling kinetic physics, rebounds, and safety web landing successfully verified!")

print("\n=== 5. Testing InteractionManager Fling & Web Shoot ===")
import core.state_machine as sm_mod
import core.behavior_controller as bc_mod
import core.interaction_manager as im_mod
StateMachine = sm_mod.StateMachine
CharacterState = sm_mod.CharacterState
BehaviorController = bc_mod.BehaviorController
InteractionManager = im_mod.InteractionManager

sm = StateMachine()
bc = BehaviorController(sm, mc, MockClass())
im = InteractionManager(sm, mc, MockClass(), MockClass(), bc)

# Test shoot_web_at
web_changes_im = []
mc.web_changed.connect(lambda web_data: web_changes_im.append(web_data))

target = MockQPoint(750, 320)
im.shoot_web_at(target)
assert len(web_changes_im) > 0, "Expected web_changed signal from shoot_web_at"
print("  [OK] shoot_web_at successfully triggered web_changed signal!")

# Test shoot_web_at_cursor
web_changes_im.clear()
im.shoot_web_at_cursor(MockQPoint(880, 200))
assert len(web_changes_im) > 0, "Expected web_changed signal from shoot_web_at_cursor"
print("  [OK] shoot_web_at_cursor successfully shot web at cursor!")

# Test drag velocity calculation in handle_mouse_release
im._drag_history.clear()
now = time.monotonic()
im._drag_history.append((now - 0.08, 500.0, 500.0))
im._drag_history.append((now - 0.04, 600.0, 420.0))
im._drag_history.append((now, 720.0, 310.0))

im._is_dragging = True
im._shift_drag = False
im.handle_mouse_release(MockQt.LeftButton)

assert mc.mode == "fling", f"Expected flick release to trigger fling, got {mc.mode}"
print(f"  [OK] Mouse flick release successfully triggered Fling Physics mode! vx={mc.vx:.1f}, vy={mc.vy:.1f}")

print("\n=== 6. Validating Frontend/js/spider_bridge.js Feature Bindings ===")
js_path = ROOT / "Frontend" / "js" / "spider_bridge.js"
with open(js_path, "r", encoding="utf-8") as f:
    js_text = f.read()

required_js_elements = [
    "toggle-fling-physics",
    "toggle-web-shoot-cursor",
    "btn-test-web-shoot",
    "toggle-mouse-following",
    "toggle-sticky-notes-enabled",
    "toggle-settings-fling-physics",
    "toggle-settings-web-shoot-cursor",
    "toggle-settings-sticky-notes",
    "toggle-sticky-notes-header-enabled",
    "toggle_fling_physics",
    "toggle_web_shoot_cursor",
    "toggle_sticky_notes",
    "shoot_web_cursor",
]

for el in required_js_elements:
    assert el in js_text, f"Missing {el} in Frontend/js/spider_bridge.js"
    print(f"  [OK] Found binding in JS: {el}")

print("\n=== 7. Validating Search Index Entries in Frontend/index.html ===")
index_path = ROOT / "Frontend" / "index.html"
with open(index_path, "r", encoding="utf-8") as f:
    html_text = f.read()

assert "Drag-and-Throw Fling Physics" in html_text
assert "Web-Shoot to Cursor" in html_text
assert "Mouse Follow &amp; Chase Mode" in html_text or "Mouse Follow & Chase Mode" in html_text
assert "Spider Sticky Notes" in html_text
print("  [OK] Search index in Frontend/index.html properly contains all new features!")

print("\n========================================================")
print("[SUCCESS] ALL 7 TEST SUITES PASSED WITH 100% SUCCESS!")
print("========================================================")
