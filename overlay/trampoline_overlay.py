"""Interactive Web Trampoline overlay with 2D spring physics deflection and dissolve animation."""
import math
import random
import time
from typing import List, Optional, Tuple
from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


class TrampolineOverlay(QWidget):
    """
    Renders an interactive spider-web trampoline drawn between two points.
    Deflects dynamically using a damped 2D harmonic spring model when Spider-Man
    hits it, then recoils and dissolves into glowing spider-silk particles.
    """

    # Emitted when trampoline dissolves or expires
    trampoline_dissolved = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(
            parent,
            Qt.Tool
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.WindowTransparentForInput
            | Qt.WindowDoesNotAcceptFocus,
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.NoFocus)

        self._p1 = QPointF(0, 0)
        self._p2 = QPointF(0, 0)
        self._is_active = False

        # Spring dynamics state
        self._bounce_time = 0.0
        self._is_bouncing = False
        self._bounce_amplitude = 0.0
        self._bounce_normal = QPointF(0, 1)

        # Dissolve state
        self._created_time = 0.0
        self._dissolve_time = 0.0
        self._is_dissolving = False
        self._max_lifetime = 16.0  # max 16s before auto-dissolving
        self._particles: List[dict] = []

        # 60 FPS animation loop
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(16)
        self._anim_timer.timeout.connect(self._on_anim_frame)

    def set_trampoline(self, p1: QPointF, p2: QPointF) -> None:
        """Initialize and display an interactive trampoline strand between p1 and p2."""
        self._p1 = QPointF(p1)
        self._p2 = QPointF(p2)
        self._is_active = True
        self._is_bouncing = False
        self._is_dissolving = False
        self._created_time = time.monotonic()
        self._particles.clear()

        # Update bounding geometry
        self._update_geometry()
        self.show()
        self.raise_()
        self._anim_timer.start()
        self.update()

    def _update_geometry(self) -> None:
        """Size and position window to cover the trampoline strand with spring margins."""
        min_x = min(self._p1.x(), self._p2.x()) - 40
        min_y = min(self._p1.y(), self._p2.y()) - 50
        max_x = max(self._p1.x(), self._p2.x()) + 40
        max_y = max(self._p1.y(), self._p2.y()) + 70

        width = max(100.0, max_x - min_x)
        height = max(80.0, max_y - min_y)

        self.setGeometry(int(min_x), int(min_y), int(width), int(height))

    def trigger_bounce(self, impact_speed: float = 600.0) -> None:
        """Trigger dynamic 2D spring deflection when Spider-Man hits the web."""
        self._is_bouncing = True
        self._bounce_time = time.monotonic()
        # Deflection amplitude scaled by impact velocity (clamped)
        self._bounce_amplitude = max(24.0, min(55.0, impact_speed * 0.055))

        # Calculate unit normal vector pointing downwards (deflection direction)
        dx = self._p2.x() - self._p1.x()
        dy = self._p2.y() - self._p1.y()
        length = max(1.0, math.hypot(dx, dy))

        # Perpendicular normal: (-dy/L, dx/L). Ensure positive Y (downward deflection)
        nx = -dy / length
        ny = dx / length
        if ny < 0:
            nx, ny = -nx, -ny
        self._bounce_normal = QPointF(nx, ny)

        # Schedule dissolving 1.4s after the bounce
        QTimer.singleShot(1400, self.start_dissolve)
        self.update()

    def start_dissolve(self) -> None:
        """Begin dissolving the web strand into fading silk particles."""
        if self._is_dissolving:
            return
        self._is_dissolving = True
        self._dissolve_time = time.monotonic()

        # Generate sparkling web particles along the strand
        dx = self._p2.x() - self._p1.x()
        dy = self._p2.y() - self._p1.y()
        count = 28
        self._particles = []
        for i in range(count):
            t = i / float(count - 1)
            px = self._p1.x() + dx * t
            py = self._p1.y() + dy * t
            self._particles.append({
                "x": px,
                "y": py,
                "vx": (random.random() - 0.5) * 80.0,
                "vy": -random.random() * 60.0 - 15.0,
                "size": random.uniform(2.0, 4.5),
                "alpha": 1.0,
            })

    def is_active(self) -> bool:
        return self._is_active

    def get_endpoints(self) -> Tuple[QPointF, QPointF]:
        return self._p1, self._p2

    def remove(self) -> None:
        """Immediately remove and hide trampoline."""
        self._is_active = False
        self._anim_timer.stop()
        self.hide()
        self.trampoline_dissolved.emit()

    def _on_anim_frame(self) -> None:
        if not self._is_active:
            self._anim_timer.stop()
            return

        now = time.monotonic()

        # Check max lifetime
        if not self._is_dissolving and (now - self._created_time > self._max_lifetime):
            self.start_dissolve()

        if self._is_dissolving:
            elapsed = now - self._dissolve_time
            if elapsed > 0.8:
                self.remove()
                return
            # Update particles
            dt = 0.016
            for p in self._particles:
                p["x"] += p["vx"] * dt
                p["y"] += p["vy"] * dt
                p["vy"] += 45.0 * dt  # light gravity
                p["alpha"] = max(0.0, 1.0 - (elapsed / 0.8))

        self.update()

    def nativeEvent(self, event_type, message):
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

        painter.setRenderHint(QPainter.Antialiasing)

        # Coordinate transform from global to local widget coordinates
        ox = float(self.x())
        oy = float(self.y())
        p1 = QPointF(self._p1.x() - ox, self._p1.y() - oy)
        p2 = QPointF(self._p2.x() - ox, self._p2.y() - oy)

        now = time.monotonic()

        # 1. Calculate spring deflection
        deflection_mag = 0.0
        if self._is_bouncing:
            t = now - self._bounce_time
            # Damped 2D harmonic oscillator: A * cos(omega * t) * exp(-zeta * t)
            omega = 26.0  # spring oscillation speed
            zeta = 4.2    # damping decay
            deflection_mag = self._bounce_amplitude * math.cos(omega * t) * math.exp(-zeta * t)

        # Midpoint with spring sag/rebound
        mid_x = (p1.x() + p2.x()) * 0.5 + self._bounce_normal.x() * deflection_mag
        mid_y = (p1.y() + p2.y()) * 0.5 + self._bounce_normal.y() * deflection_mag

        opacity = 1.0
        if self._is_dissolving:
            elapsed = now - self._dissolve_time
            opacity = max(0.0, 1.0 - (elapsed / 0.75))

        painter.setOpacity(opacity)

        # ==========================================
        # 1. Anchor Knots at Endpoints
        # ==========================================
        for pt in (p1, p2):
            # Outer glow
            painter.setBrush(QColor(0, 180, 255, 80))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(pt, 6.0, 6.0)
            # Core silk knot
            painter.setBrush(QColor(245, 250, 255, 240))
            painter.setPen(QPen(QColor(0, 210, 255, 200), 1.2))
            painter.drawEllipse(pt, 3.5, 3.5)

        # ==========================================
        # 2. Trampoline Web Strand (Bowed Spring Path)
        # ==========================================
        web_path = QPainterPath()
        web_path.moveTo(p1)
        web_path.quadTo(QPointF(mid_x, mid_y), p2)

        # Outer electric-blue web tension glow
        glow_pen = QPen(QColor(0, 210, 255, 110), 4.5)
        painter.setPen(glow_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(web_path)

        # Core reinforced spider-silk strand
        core_pen = QPen(QColor(245, 250, 255, 230), 2.2)
        painter.setPen(core_pen)
        painter.drawPath(web_path)

        # Tension cross-threads (little silk webbing threads along the strand)
        steps = 6
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        for s in range(1, steps):
            u = s / float(steps)
            # Quadratic point on Bezier
            bx = (1 - u)**2 * p1.x() + 2 * (1 - u) * u * mid_x + u**2 * p2.x()
            by = (1 - u)**2 * p1.y() + 2 * (1 - u) * u * mid_y + u**2 * p2.y()
            # Small cross knot
            painter.setPen(QPen(QColor(230, 245, 255, 180), 1.0))
            painter.drawLine(QPointF(bx - 3, by - 3), QPointF(bx + 3, by + 3))

        # ==========================================
        # 3. Dissolve Silk Sparkle Particles
        # ==========================================
        if self._is_dissolving:
            for p in self._particles:
                alpha = int(p["alpha"] * 240)
                if alpha <= 0:
                    continue
                painter.setBrush(QColor(0, 220, 255, alpha))
                painter.setPen(Qt.NoPen)
                lx = p["x"] - ox
                ly = p["y"] - oy
                painter.drawEllipse(QPointF(lx, ly), p["size"], p["size"])
