"""Comic-style speech bubbles and Spider-Sense visual effects overlay."""
import math
import random
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
    QPolygonF,
)
from PySide6.QtWidgets import QWidget


class ComicEffectsOverlay(QWidget):
    """
    Transparent floating companion overlay for Spider-Man that renders:
    1. ⚡ "Spider-Sense" radiating comic squiggles and lightning shockwaves.
    2. Stylized comic speech and reaction bubbles with spring floating animations.
    """

    def __init__(self, pet_overlay, movement, parent: Optional[QWidget] = None):
        super().__init__(
            parent,
            Qt.Tool
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.WindowTransparentForInput
            | Qt.WindowDoesNotAcceptFocus,
        )
        self.pet = pet_overlay
        self.movement = movement

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.NoFocus)

        self._width = 340
        self._height = 240
        self.resize(self._width, self._height)

        # Spider-Sense state
        self._spider_sense_active = False
        self._spider_sense_start = 0.0
        self._spider_sense_duration = 0.75
        self._spider_bolts = []

        # Speech bubble state
        self._bubble_active = False
        self._bubble_text = ""
        self._bubble_style = "comic"  # "comic", "action", "glitch"
        self._bubble_start = 0.0
        self._bubble_duration = 2.0
        self._bubble_width = 140
        self._bubble_height = 48

        # 60 FPS animation loop
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(16)
        self._anim_timer.timeout.connect(self._on_anim_frame)

        self._update_geometry()

    def update_pet_position(self, x: int, y: int):
        self._update_geometry()

    def update_pet_size(self, w: int, h: int):
        self._update_geometry()

    def _update_geometry(self):
        """Keep the effect canvas centered over Spider-Man's head."""
        if not self.movement:
            return
        pet_w = getattr(self.movement, "width", 128)
        pet_h = getattr(self.movement, "height", 128)
        pet_x = getattr(self.movement, "x", 300)
        pet_y = getattr(self.movement, "y", 300)

        center_x = pet_x + pet_w / 2.0
        head_y = pet_y

        target_x = int(center_x - self._width / 2.0)
        target_y = int(head_y - self._height + 40)

        # Ensure we stay mostly visible on screen
        if target_y < 0:
            target_y = max(0, int(head_y + 10))  # Flip below if pushed off top screen

        self.move(target_x, target_y)

    def trigger_spider_sense(self, duration_ms: int = 750):
        """⚡ Trigger radiating comic-style Spider-Sense lightning squiggles over his head."""
        self._spider_sense_active = True
        self._spider_sense_start = time.monotonic()
        self._spider_sense_duration = max(0.2, duration_ms / 1000.0)

        # Generate fresh randomized zigzag lightning bolts fanning outward
        self._spider_bolts = self._generate_spider_sense_bolts()

        self._update_geometry()
        self._start_anim_if_needed()
        self.show()
        self.update()

    def _generate_spider_sense_bolts(self):
        """Generate 7 radiating comic zigzag lightning squiggles."""
        bolts = []
        # Fanning angles from -65 deg to +65 deg around vertical (90 deg up)
        angles_deg = [-65, -45, -25, -8, 8, 25, 45, 65]
        for idx, ang in enumerate(angles_deg):
            rad = math.radians(90 - ang)
            length = random.uniform(50.0, 75.0)
            segments = random.randint(3, 4)
            bolts.append({
                "angle": rad,
                "length": length,
                "segments": segments,
                "color_type": "yellow" if (idx % 2 == 0) else "crimson",
                "seed": random.uniform(0.8, 1.2),
            })
        return bolts

    def show_bubble(self, text: str, duration_ms: int = 2200, style: str = "comic"):
        """Display stylized comic dialogue or reaction bubble."""
        if not text:
            return
        self._bubble_text = str(text).strip()
        self._bubble_style = style
        self._bubble_start = time.monotonic()
        self._bubble_duration = max(0.8, duration_ms / 1000.0)
        self._bubble_active = True

        self._update_geometry()
        self._start_anim_if_needed()
        self.show()
        self.update()

    def hide_bubble(self):
        self._bubble_active = False
        self.update()

    def _start_anim_if_needed(self):
        if not self._anim_timer.isActive():
            self._anim_timer.start()

    def _on_anim_frame(self):
        now = time.monotonic()
        needs_redraw = False

        # Check spider-sense expiry
        if self._spider_sense_active:
            elapsed = now - self._spider_sense_start
            if elapsed >= self._spider_sense_duration:
                self._spider_sense_active = False
            needs_redraw = True

        # Check bubble expiry
        if self._bubble_active:
            elapsed = now - self._bubble_start
            if elapsed >= self._bubble_duration:
                self._bubble_active = False
            needs_redraw = True

        # Stop timer if both inactive
        if not self._spider_sense_active and not self._bubble_active:
            self._anim_timer.stop()
            self.hide()
            return

        if needs_redraw:
            self._update_geometry()
            self.update()

    def paintEvent(self, event):
        if not self._spider_sense_active and not self._bubble_active:
            return

        now = time.monotonic()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        # 1. Render Spider-Sense Squiggles if active
        if self._spider_sense_active:
            self._draw_spider_sense(painter, now)

        # 2. Render Comic Speech Bubble if active
        if self._bubble_active:
            self._draw_speech_bubble(painter, now)

        painter.end()

    def _draw_spider_sense(self, painter: QPainter, now: float):
        """Draw radiating comic lightning squiggles and tingling crown over Spider-Man's head."""
        elapsed = now - self._spider_sense_start
        progress = max(0.0, min(1.0, elapsed / self._spider_sense_duration))

        # Pulsing expansion & fading alpha
        if progress < 0.2:
            scale_pulse = progress / 0.2
            alpha = 1.0
        elif progress > 0.7:
            scale_pulse = 1.0 + (progress - 0.7) * 0.3
            alpha = max(0.0, (1.0 - progress) / 0.3)
        else:
            scale_pulse = 1.0 + 0.1 * math.sin(progress * math.pi * 6)
            alpha = 1.0

        # Anchor point (center bottom, right above mask)
        cx = self._width / 2.0
        cy = self._height - 25.0

        jitter_phase = int(elapsed * 25.0)

        for bolt in self._spider_bolts:
            ang = bolt["angle"]
            base_len = bolt["length"] * scale_pulse
            segs = bolt["segments"]
            col_type = bolt["color_type"]

            # Compute zigzag points
            points = [QPointF(cx, cy)]
            dx = math.cos(ang)
            dy = -math.sin(ang)

            # Perpendicular vector for zig-zag
            px = -dy
            py = dx

            step_len = base_len / segs
            for s in range(1, segs + 1):
                t = s / segs
                # Add high-frequency comic zigzag kink
                kink_dir = 1.0 if (s % 2 == 1) else -1.0
                kink_mag = random.choice([7.0, 9.0, -8.0, 10.0]) if (s < segs) else 0.0
                # Animate jitter
                kink_mag += 2.0 * math.sin(jitter_phase + s)

                nx = cx + dx * (s * step_len) + px * kink_mag
                ny = cy + dy * (s * step_len) + py * kink_mag
                points.append(QPointF(nx, ny))

            # Draw outer dark comic outline (thick comic book ink)
            outline_pen = QPen(QColor(15, 23, 42, int(240 * alpha)), 4.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(outline_pen)
            for i in range(len(points) - 1):
                painter.drawLine(points[i], points[i + 1])

            # Draw vibrant electric core
            if col_type == "yellow":
                core_color = QColor(255, 235, 0, int(255 * alpha))   # Intense Electric Yellow
            else:
                core_color = QColor(255, 30, 80, int(255 * alpha))    # Comic Scarlet / Crimson

            core_pen = QPen(core_color, 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(core_pen)
            for i in range(len(points) - 1):
                painter.drawLine(points[i], points[i + 1])

            # Mini spark star at bolt tip
            tip = points[-1]
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(255, 255, 255, int(230 * alpha)))
            painter.drawEllipse(tip, 2.0, 2.0)

        # Center comic energy spark ⚡
        spark_pen = QPen(QColor(255, 230, 0, int(220 * alpha)), 2.0)
        painter.setPen(spark_pen)
        painter.setFont(QFont("Segoe UI Emoji", 14, QFont.Bold))
        painter.drawText(QRectF(cx - 16, cy - 28, 32, 28), Qt.AlignCenter, "⚡")

    def _draw_speech_bubble(self, painter: QPainter, now: float):
        """Draw stylized pop-up comic dialogue bubble with floating spring animation."""
        elapsed = now - self._bubble_start
        duration = self._bubble_duration
        progress = max(0.0, min(1.0, elapsed / duration))

        # Floating Spring Animation:
        # 1. Pop-in bounce (first 0.22s)
        if elapsed < 0.22:
            t = elapsed
            scale = 0.5 + 0.6 * (1.0 + 0.3 * math.exp(-14 * t) * math.sin(18 * t))
            opacity = min(1.0, elapsed / 0.08)
        # 2. Fade out (last 0.22s)
        elif elapsed > duration - 0.22:
            t_rem = duration - elapsed
            scale = max(0.7, t_rem / 0.22)
            opacity = max(0.0, t_rem / 0.22)
        # 3. Floating hover
        else:
            scale = 1.0
            opacity = 1.0

        float_y = 3.5 * math.sin(elapsed * 4.0)

        # Select comic font
        font = QFont("Impact", 13)
        if not font.exactMatch():
            font = QFont("Arial Black", 12)
        font.setBold(True)
        painter.setFont(font)

        fm = QFontMetrics(font)
        text_rect = fm.boundingRect(self._bubble_text)
        bw = max(110.0, float(text_rect.width() + 34.0))
        bh = max(38.0, float(text_rect.height() + 18.0))

        # Center bubble horizontally
        cx = self._width / 2.0
        # Position above Spider-Man's head / squiggles
        cy = self._height - 65.0 + float_y - (30.0 if self._spider_sense_active else 0.0)

        bx = cx - bw / 2.0
        by = cy - bh

        # Save painter state for spring transform
        painter.save()
        painter.setOpacity(opacity)

        # Apply spring scaling centered at (cx, cy)
        painter.translate(cx, cy)
        painter.scale(scale, scale)
        painter.translate(-cx, -cy)

        # Build comic speech balloon path with tail
        path = QPainterPath()
        bubble_rect = QRectF(bx, by, bw, bh)
        path.addRoundedRect(bubble_rect, 14.0, 14.0)

        # Pointer tail pointing down towards Spider-Man's head
        tail_path = QPainterPath()
        tail_p1 = QPointF(cx - 8.0, by + bh - 1.0)
        tail_p2 = QPointF(cx + 8.0, by + bh - 1.0)
        tail_tip = QPointF(cx - 2.0, by + bh + 13.0)
        tail_poly = QPolygonF([tail_p1, tail_tip, tail_p2])
        tail_path.addPolygon(tail_poly)

        full_bubble = path.united(tail_path)

        # 1. Comic drop shadow
        shadow_path = QPainterPath(full_bubble)
        shadow_path.translate(3.0, 3.5)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 50))
        painter.drawPath(shadow_path)

        # 2. Bubble interior fill
        if self._bubble_style == "action":
            # Action burst style: Vibrant comic electric yellow gradient
            grad = QLinearGradient(bx, by, bx, by + bh)
            grad.setColorAt(0.0, QColor("#FFF570"))
            grad.setColorAt(1.0, QColor("#FFD000"))
            painter.setBrush(grad)
            stroke_color = QColor("#0F172A")
            text_color = QColor("#0F172A")
        elif self._bubble_style == "glitch":
            # Multiverse glitch style: Neon cyan to hot magenta split feel
            grad = QLinearGradient(bx, by, bx + bw, by + bh)
            grad.setColorAt(0.0, QColor("#F0FDFA"))
            grad.setColorAt(1.0, QColor("#FFF1F2"))
            painter.setBrush(grad)
            stroke_color = QColor("#E11D48")
            text_color = QColor("#0F172A")
        else:
            # Classic comic white bubble
            grad = QLinearGradient(bx, by, bx, by + bh)
            grad.setColorAt(0.0, QColor("#FFFFFF"))
            grad.setColorAt(1.0, QColor("#F8FAFC"))
            painter.setBrush(grad)
            stroke_color = QColor("#1E293B")
            text_color = QColor("#0F172A")

        # 3. Comic outline stroke
        stroke_pen = QPen(stroke_color, 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(stroke_pen)
        painter.drawPath(full_bubble)

        # 4. If action style, draw small action burst lines / stars
        if self._bubble_style == "action":
            painter.setPen(QPen(QColor("#E11D48"), 2.0))
            painter.drawLine(int(bx - 4), int(by + 6), int(bx - 10), int(by + 3))
            painter.drawLine(int(bx + bw + 4), int(by + 6), int(bx + bw + 10), int(by + 3))

        # 5. Render comic text
        painter.setPen(text_color)
        painter.drawText(bubble_rect, Qt.AlignCenter, self._bubble_text)

        painter.restore()
