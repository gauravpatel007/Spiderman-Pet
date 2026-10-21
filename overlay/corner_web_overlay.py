"""Comic-style corner spider-web overlay with eye-break and hydration alert."""
import math
import time
from typing import Optional
from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QApplication, QWidget


class CornerWebOverlay(QWidget):
    """
    Transparent top-right corner overlay that displays:
    1. An authentic Spider-Man corner cobweb radiating from the top-right screen vertex.
    2. A stylized comic badge: '💧 TIME FOR WATER, MAN!' with eye-break reminders.
    3. Concentric glass-tapping shockwave rings.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(
            parent,
            Qt.Tool
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.WindowDoesNotAcceptFocus,
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.NoFocus)

        self._width = 400
        self._height = 280
        self.resize(self._width, self._height)

        self._active = False
        self._start_time = 0.0
        self._duration = 8.0
        self._title = "💧 TIME FOR WATER, MAN!"
        self._subtitle = "60 minutes of hero work! Rest your eyes & hydrate!"

        # Animation timer (60 FPS)
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(16)
        self._anim_timer.timeout.connect(self._on_anim_frame)

        self._auto_close_timer = QTimer(self)
        self._auto_close_timer.setSingleShot(True)
        self._auto_close_timer.timeout.connect(self.dismiss)

        self._reposition()

    def _reposition(self) -> None:
        """Position in the top-right corner of the primary screen."""
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.geometry()
            self.move(geom.right() - self._width + 1, geom.top())
        else:
            self.move(1920 - self._width, 0)

    def show_alert(
        self,
        title: str = "💧 TIME FOR WATER, MAN!",
        subtitle: str = "60 minutes straight! Rest your eyes & take a water break!",
        duration_sec: float = 8.0,
    ) -> None:
        """Display the corner web alert with spring animation."""
        self._title = title
        self._subtitle = subtitle
        self._duration = max(3.0, float(duration_sec))
        self._start_time = time.monotonic()
        self._active = True

        self._reposition()
        self.show()
        self.raise_()
        self.update()

        self._anim_timer.start()
        self._auto_close_timer.start(int(self._duration * 1000))

    def dismiss(self) -> None:
        """Dismiss and hide the overlay."""
        self._active = False
        self._anim_timer.stop()
        self._auto_close_timer.stop()
        self.hide()

    def mousePressEvent(self, event) -> None:
        """Clicking the alert badge dismisses it."""
        self.dismiss()
        event.accept()

    def _on_anim_frame(self) -> None:
        if not self._active:
            self._anim_timer.stop()
            return
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
        if not self._active:
            return

        painter = QPainter(self)
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        painter.fillRect(self.rect(), Qt.transparent)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

        now = time.monotonic()
        elapsed = now - self._start_time
        remaining = self._duration - elapsed

        if remaining <= 0:
            self.dismiss()
            return

        # Entrance spring & exit fade opacity
        if elapsed < 0.4:
            # Spring scale 0 -> 1.08 -> 1.0
            t = elapsed / 0.4
            scale = math.sin(t * math.pi * 0.5) * 1.04
            opacity = min(1.0, elapsed / 0.25)
        elif remaining < 0.6:
            # Fade out
            scale = 1.0
            opacity = max(0.0, remaining / 0.6)
        else:
            scale = 1.0 + 0.02 * math.sin(elapsed * 3.5)
            opacity = 1.0

        painter = QPainter(self)

        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        painter.setOpacity(opacity)

        w = float(self._width)
        h = float(self._height)
        origin_x = w  # top right vertex
        origin_y = 0.0

        # ==========================================
        # 1. Authentic Spider-Man Corner Cobweb Mesh
        # ==========================================
        radial_count = 6
        max_dist = min(w, h * 1.4)
        radial_angles = [
            math.radians(180 - i * (90 / (radial_count - 1)))
            for i in range(radial_count)
        ]

        # Draw soft glowing web strands
        web_pen = QPen(QColor(230, 242, 255, 190), 1.6)
        glow_pen = QPen(QColor(40, 160, 255, 60), 3.5)

        for pen in (glow_pen, web_pen):
            painter.setPen(pen)
            # Radial lines from (origin_x, origin_y)
            for angle in radial_angles:
                rx = origin_x + max_dist * math.cos(angle)
                ry = origin_y + max_dist * math.sin(angle)
                painter.drawLine(QPointF(origin_x, origin_y), QPointF(rx, ry))

            # Concentric web cross-arcs
            ring_count = 5
            for r_idx in range(1, ring_count + 1):
                radius = max_dist * (r_idx / ring_count)
                path = QPainterPath()
                first = True
                for angle in radial_angles:
                    # Subtle sag between radials
                    ax = origin_x + radius * math.cos(angle)
                    ay = origin_y + radius * math.sin(angle)
                    if first:
                        path.moveTo(ax, ay)
                        first = False
                    else:
                        # Arc sag toward origin
                        mid_angle = angle + (math.pi / (radial_count * 2))
                        sag_r = radius * 0.93
                        cx = origin_x + sag_r * math.cos(mid_angle)
                        cy = origin_y + sag_r * math.sin(mid_angle)
                        path.quadTo(cx, cy, ax, ay)
                painter.drawPath(path)

        # ==========================================
        # 2. Glass-tapping Shockwave Rings
        # ==========================================
        tap_phase = (elapsed * 2.2) % 1.0
        tap_center = QPointF(origin_x - 110, origin_y + 80)
        for ring_offset in (0.0, 0.35, 0.7):
            phase = (tap_phase + ring_offset) % 1.0
            ring_r = 15.0 + phase * 65.0
            ring_alpha = int((1.0 - phase) * 110)
            painter.setPen(QPen(QColor(0, 220, 255, ring_alpha), 2.0))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(tap_center, ring_r, ring_r * 0.75)

        # ==========================================
        # 3. Comic Alert Badge Attached to the Web
        # ==========================================
        badge_w = 320.0 * scale
        badge_h = 100.0 * scale
        badge_x = (w - badge_w) * 0.5 + 20.0
        badge_y = 60.0 + (1.0 - scale) * 20.0

        badge_rect = QRectF(badge_x, badge_y, badge_w, badge_h)

        # Background with stylish Spider-Man gradient & dark comic slate
        bg_gradient = QLinearGradient(badge_x, badge_y, badge_x + badge_w, badge_y + badge_h)
        bg_gradient.setColorAt(0.0, QColor(16, 20, 38, 245))
        bg_gradient.setColorAt(0.7, QColor(10, 14, 28, 250))
        bg_gradient.setColorAt(1.0, QColor(22, 12, 28, 250))

        painter.setBrush(bg_gradient)
        painter.setPen(QPen(QColor(226, 54, 54, 230), 2.5))  # Spider-Red border
        painter.drawRoundedRect(badge_rect, 14.0, 14.0)

        # Inner cyan accent border
        inner_rect = badge_rect.adjusted(3, 3, -3, -3)
        painter.setPen(QPen(QColor(0, 210, 255, 120), 1.0))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(inner_rect, 11.0, 11.0)

        # Web attachment corner stitches
        painter.setPen(QPen(QColor(240, 245, 255, 220), 1.8))
        painter.drawLine(QPointF(origin_x, origin_y), QPointF(badge_x + badge_w - 20, badge_y))
        painter.drawLine(QPointF(origin_x - 40, origin_y), QPointF(badge_x + 30, badge_y))

        # Typography
        # Title: TIME FOR WATER, MAN!
        title_font = QFont("Segoe UI", int(13 * scale), QFont.Bold)
        painter.setFont(title_font)
        painter.setPen(QColor(0, 225, 255, 255))  # Electric cyan
        painter.drawText(
            QRectF(badge_x + 16, badge_y + 12, badge_w - 32, 28),
            Qt.AlignLeft | Qt.AlignVCenter,
            self._title,
        )

        # Subtitle message
        sub_font = QFont("Segoe UI", int(10 * scale), QFont.Normal)
        painter.setFont(sub_font)
        painter.setPen(QColor(230, 235, 245, 240))
        painter.drawText(
            QRectF(badge_x + 16, badge_y + 40, badge_w - 32, 42),
            Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap,
            self._subtitle,
        )

        # Small click to dismiss cue
        hint_font = QFont("Segoe UI", int(8 * scale), QFont.Normal)
        painter.setFont(hint_font)
        painter.setPen(QColor(160, 175, 200, 170))
        painter.drawText(
            QRectF(badge_x + 16, badge_y + badge_h - 20, badge_w - 32, 16),
            Qt.AlignRight | Qt.AlignVCenter,
            "Click to dismiss ✕",
        )
