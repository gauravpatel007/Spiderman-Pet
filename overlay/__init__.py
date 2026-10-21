"""Overlay, window tracking, and monitor boundary management package."""
from .hit_test_manager import HitTestManager
from .monitor_manager import MonitorManager
# pyrefly: ignore [missing-import]
from .boundary_controller import BoundaryController
from .window_detector import WindowDetector, WindowInfo
from .window_tracker import WindowTracker
# pyrefly: ignore [missing-import]
from .transparent_overlay import TransparentOverlay
# pyrefly: ignore [missing-import]
from .overlay_manager import OverlayManager
from .corner_web_overlay import CornerWebOverlay
from .trampoline_overlay import TrampolineOverlay

__all__ = [
    "HitTestManager",
    "MonitorManager",
    "BoundaryController",
    "WindowDetector",
    "WindowInfo",
    "WindowTracker",
    "TransparentOverlay",
    "OverlayManager",
    "CornerWebOverlay",
    "TrampolineOverlay",
]
