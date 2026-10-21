"""Comic-style speech bubbles and Spider-Sense visual effects overlay."""
import math
import random
import time
from typing import Optional
from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, QTimer, QEvent
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
from PySide6.QtWidgets import QApplication, QWidget


class ComicEffectsOverlay(QWidget):
    """
    Transparent floating companion overlay for Spider-Man that renders:
    1. ⚡ "Spider-Sense" radiating comic squiggles and lightning shockwaves.
    2. Stylized comic speech and reaction bubbles with spring floating animations.
    """

    def __init__(self, pet_overlay, movement, parent: Optional[QWidget] = None):
        super().__init__(
            parent if parent is not None else pet_overlay,
            Qt.Tool
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.WindowTransparentForInput
            | Qt.WindowDoesNotAcceptFocus,
        )
        self.pet = pet_overlay
        self.movement = movement
        self.pet.installEventFilter(self)

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.NoFocus)

        self._width = 380
        self._height = 260
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

        # Heavy load (>85% CPU/RAM) collapsing steel beam state
        self._heavy_load_active = False
        self._heavy_cpu = 0.0
        self._heavy_ram = 0.0
        self._rubble_particles = []

        # Audio & music synchronization state
        self._music_active = False
        self._music_volume = 0.0
        self._music_notes = []
        self._soundwave_rings = []
        self._last_note_spawn = 0.0

        # Battery charging yellow floating indicator state
        self._charging_active = False
        self._battery_percent = 100
        self._character_id = "miles_morales"
        self._is_inverted = False
        self._current_activity = ""

        # 60 FPS animation loop
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(16)
        self._anim_timer.timeout.connect(self._on_anim_frame)

        self._update_geometry()

    def set_orientation(self, deg: float):
        """Update orientation to adjust indicator position when character hangs upside down."""
        try:
            self._is_inverted = abs(float(deg) - 180.0) < 45.0
        except Exception:
            self._is_inverted = False
        self._update_geometry()
        self.update()

    def set_activity(self, name: str):
        """Set active activity name (e.g. title_hang for upside down, title_perch for upright)."""
        self._current_activity = str(name)
        if name == "title_hang":
            self._is_inverted = True
        elif name == "title_perch":
            self._is_inverted = False
        self._update_geometry()
        self.update()

    def is_inverted(self) -> bool:
        if getattr(self, '_is_inverted', False):
            return True
        if hasattr(self, 'pet') and hasattr(self.pet, '_pose_rotation'):
            try:
                if abs(float(self.pet._pose_rotation) - 180.0) < 45.0:
                    return True
            except Exception:
                pass
        return False

    def set_battery_charging(self, is_charging: bool, percent: int = 100, character_id: str = ""):
        """Display stylish yellow floating battery indicator above or below cartoon's head."""
        from services.settings_service import get_settings
        if not get_settings().get('behavior.enable_battery_charging_reaction', True):
            is_charging = False

        self._charging_active = bool(is_charging)
        self._battery_percent = int(percent)
        if character_id:
            self._character_id = character_id

        if self._charging_active:
            self._update_geometry()
            self._start_anim_if_needed()
            self.show()

        self.update()


    def set_heavy_load(self, is_heavy: bool, cpu: float = 0.0, ram: float = 0.0):
        """Set heavy system load state (>85%) to render classic collapsing steel beam scene."""
        self._heavy_load_active = bool(is_heavy)
        self._heavy_cpu = float(cpu)
        self._heavy_ram = float(ram)
        if self._heavy_load_active:
            self._update_geometry()
            self._start_anim_if_needed()
            self.show()
        self.update()

    def set_music_playing(self, is_playing: bool, volume: float = 0.0):
        """Set live audio/music state to display floating cartoon musical notes and beat waves."""
        self._music_active = bool(is_playing)
        self._music_volume = float(volume)
        if self._music_active:
            self._update_geometry()
            self._start_anim_if_needed()
            self.show()
        self.update()

    def trigger_beat(self, intensity: float = 1.0):
        """Spawn energetic soundwave rings and floating cartoon musical notes on beat hit."""
        intensity = max(0.4, min(2.0, float(intensity)))
        cx = self._width / 2.0
        cy = self._height - 35.0

        # Spawn left & right expanding soundwave pulse rings
        for side_x in (cx - 42.0, cx + 42.0):
            self._soundwave_rings.append({
                "x": side_x,
                "y": cy - 10.0,
                "radius": 10.0,
                "max_radius": 38.0 * intensity,
                "speed": 65.0 * intensity,
                "opacity": 0.95,
                "color": random.choice(["#00E5FF", "#FF007F", "#FFE600", "#FF1744"]),
                "side": -1 if side_x < cx else 1,
            })

        # Spawn 1 or 2 cartoon floating notes on beat
        symbols = ["♪", "♫", "♬", "♩", "𝄞"]
        colors = ["#00E5FF", "#FF007F", "#FFE600", "#FF1744", "#A855F7", "#38BDF8"]
        num_notes = 2 if intensity > 1.2 else 1
        for _ in range(num_notes):
            spawn_side = random.choice([-1, 1])
            self._music_notes.append({
                "symbol": random.choice(symbols),
                "x": cx + spawn_side * random.uniform(28.0, 58.0),
                "y": cy - random.uniform(10.0, 30.0),
                "vx": spawn_side * random.uniform(0.6, 1.8),
                "vy": random.uniform(35.0, 55.0) * intensity,
                "color": random.choice(colors),
                "size": random.randint(15, 22),
                "rotation": random.uniform(-18.0, 18.0),
                "rot_speed": random.uniform(-25.0, 25.0),
                "age": 0.0,
                "lifetime": random.uniform(1.4, 2.2),
                "sway_phase": random.uniform(0.0, 6.28),
            })

        self._start_anim_if_needed()
        self.show()
        self.update()

    def update_pet_position(self, x: int, y: int):
        self._update_geometry()

    def eventFilter(self, watched, event):
        if watched is getattr(self, "pet", None) and hasattr(self, "_anim_timer"):
            if event.type() == QEvent.Hide:
                self.hide()
                self._anim_timer.stop()
            elif event.type() == QEvent.Show:
                self._update_geometry()
                self._start_anim_if_needed()
                self.show()
        return super().eventFilter(watched, event)

    def show(self):
        # Service updates may arrive while paused or outside the selected app.
        if self.pet.isVisible():
            super().show()

    def update_pet_size(self, w: int, h: int):
        self._update_geometry()

    def _update_geometry(self):
        """Keep the effect canvas centered over/under Spider-Man's head."""
        if not self.movement:
            return

        # position_changed can reach this slot before QWidget.move. Use the
        # current physics snapshot, not the pet widget's previous coordinates.
        pet_w = self.pet.width()
        pet_h = self.pet.height()
        pet_x = round(self.movement.x)
        pet_y = round(self.movement.y)

        center_x = pet_x + pet_w / 2.0
        target_x = int(center_x - self._width / 2.0)

        inverted = self.is_inverted()
        if inverted:
            # Activity 6 (title_hang): character is upside-down, head is at the bottom
            # Shifted slightly further down below the upside-down head per user request
            head_bottom_y = pet_y + int(pet_h * 0.87)
            screen_badge_y = head_bottom_y + 32.0
            target_y = int(screen_badge_y - 40.0)
        else:
            # Activity 7 (title_perch), Activity 3 (walk), and upright poses: head is at the top
            # Placed exact above head with snug 4-6px gap like in activity 3!
            head_top_y = pet_y + int(pet_h * 0.13)
            screen_badge_y = head_top_y - 18.0
            target_y = int(screen_badge_y - 40.0)

        # Keep clamped to visible top edge without jumping below
        screen = QApplication.screenAt(QPoint(int(center_x), int(pet_y + pet_h / 2)))
        if screen:
            target_y = max(screen.availableGeometry().top(), target_y)

        if self.pos() != QPoint(target_x, target_y):
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
        if self.pet.isVisible() and not self._anim_timer.isActive():
            self._anim_timer.start()

    def _on_anim_frame(self):
        if not self.pet.isVisible():
            self.hide()
            self._anim_timer.stop()
            return
        now = time.monotonic()
        dt = 0.016
        needs_redraw = False

        # 1. Check spider-sense expiry
        if self._spider_sense_active:
            elapsed = now - self._spider_sense_start
            if elapsed >= self._spider_sense_duration:
                self._spider_sense_active = False
            needs_redraw = True

        # 2. Check bubble expiry
        if self._bubble_active:
            elapsed = now - self._bubble_start
            if elapsed >= self._bubble_duration:
                self._bubble_active = False
            needs_redraw = True

        # 3. Animate heavy load falling rubble / dust specks
        if self._heavy_load_active:
            needs_redraw = True
            # Spawn new falling dust / concrete rubble
            if random.random() < 0.35:
                cx = self._width / 2.0
                self._rubble_particles.append({
                    "x": cx + random.uniform(-110.0, 110.0),
                    "y": self._height - 60.0 + random.uniform(-6.0, 6.0),
                    "vx": random.uniform(-0.8, 0.8),
                    "vy": random.uniform(1.8, 4.2),
                    "size": random.uniform(2.0, 4.5),
                    "life": 1.0,
                    "decay": random.uniform(0.02, 0.04),
                    "color": random.choice(["#94A3B8", "#64748B", "#CBD5E1", "#E2E8F0"]),
                })

        # Advance rubble
        if self._rubble_particles:
            needs_redraw = True
            active_rubble = []
            for p in self._rubble_particles:
                p["x"] += p["vx"]
                p["y"] += p["vy"]
                p["life"] -= p["decay"]
                if p["life"] > 0 and p["y"] < self._height + 15:
                    active_rubble.append(p)
            self._rubble_particles = active_rubble

        # 4. Animate soundwave rings
        if self._soundwave_rings:
            needs_redraw = True
            active_rings = []
            for r in self._soundwave_rings:
                r["radius"] += r["speed"] * dt
                r["opacity"] = max(0.0, 1.0 - (r["radius"] / r["max_radius"]))
                if r["radius"] < r["max_radius"] and r["opacity"] > 0.05:
                    active_rings.append(r)
            self._soundwave_rings = active_rings

        # 5. Animate floating musical notes
        if self._music_active:
            needs_redraw = True
            # Continuous spontaneous note spawn while music is playing
            if (now - self._last_note_spawn) > 0.45:
                self._last_note_spawn = now
                self.trigger_beat(random.uniform(0.8, 1.2))

        if self._music_notes:
            needs_redraw = True
            active_notes = []
            for note in self._music_notes:
                note["age"] += dt
                note["y"] -= note["vy"] * dt
                note["x"] += math.sin(note["sway_phase"] + note["age"] * 3.5) * 0.9
                note["rotation"] += note["rot_speed"] * dt
                if note["age"] < note["lifetime"] and note["y"] > 5:
                    active_notes.append(note)
            self._music_notes = active_notes

        if self._charging_active:
            needs_redraw = True

        # Check if everything is idle
        has_active_effects = (
            self._spider_sense_active
            or self._bubble_active
            or self._heavy_load_active
            or self._music_active
            or self._charging_active
            or bool(self._soundwave_rings)
            or bool(self._music_notes)
            or bool(self._rubble_particles)
        )
        if not has_active_effects:
            self._anim_timer.stop()
            self.hide()
            return

        if needs_redraw:
            self._update_geometry()
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
        painter.setRenderHint(QPainter.TextAntialiasing)

        # 1. Render live music soundwaves and floating cartoon notes
        if self._soundwave_rings or self._music_notes:
            self._draw_music_effects(painter, now)

        # 2. Render classic collapsing industrial steel I-beam scene (>85% load)
        if self._heavy_load_active:
            self._draw_collapsing_beam(painter, now)

        # 3. Render Spider-Sense Squiggles if active
        if self._spider_sense_active:
            self._draw_spider_sense(painter, now)

        # 4. Render Comic Speech Bubble if active
        if self._bubble_active:
            self._draw_speech_bubble(painter, now)

        # 5. Render Yellow Battery Charging Indicator strictly above cartoon's head
        if self._charging_active:
            self._draw_charging_indicator(painter, now)

        painter.end()

    def _draw_music_effects(self, painter: QPainter, now: float):
        """Render floating cartoon musical notes and expanding neon headphone soundwave pulse rings."""
        painter.save()

        # 1. Render Soundwave Rings
        for r in self._soundwave_rings:
            alpha = int(255 * max(0.0, min(1.0, r["opacity"])))
            col = QColor(r["color"])
            col.setAlpha(alpha)
            ring_pen = QPen(col, 2.8, Qt.SolidLine, Qt.RoundCap)
            painter.setPen(ring_pen)
            painter.setBrush(Qt.NoBrush)

            rad = r["radius"]
            ring_rect = QRectF(r["x"] - rad, r["y"] - rad, rad * 2.0, rad * 2.0)
            if r["side"] < 0:
                painter.drawArc(ring_rect, int(110 * 16), int(140 * 16))
            else:
                painter.drawArc(ring_rect, int(-70 * 16), int(140 * 16))

        # 2. Render Cartoon Floating Musical Notes
        for note in self._music_notes:
            progress = note["age"] / note["lifetime"]
            if progress < 0.15:
                alpha = progress / 0.15
            elif progress > 0.75:
                alpha = (1.0 - progress) / 0.25
            else:
                alpha = 1.0
            alpha = max(0.0, min(1.0, alpha))

            painter.save()
            painter.translate(note["x"], note["y"])
            painter.rotate(note["rotation"])

            note_font = QFont("Segoe UI Symbol", note["size"])
            note_font.setBold(True)
            painter.setFont(note_font)

            painter.setPen(QColor(15, 23, 42, int(220 * alpha)))
            painter.drawText(QRectF(-16, -16, 32, 32), Qt.AlignCenter, note["symbol"])

            core_col = QColor(note["color"])
            core_col.setAlpha(int(255 * alpha))
            painter.setPen(core_col)
            painter.drawText(QRectF(-17, -17, 32, 32), Qt.AlignCenter, note["symbol"])

            spark_col = QColor(255, 255, 255, int(210 * alpha))
            painter.setPen(spark_col)
            painter.setFont(QFont("Segoe UI Symbol", 8))
            painter.drawText(QPointF(8.0, -6.0), "✦")

            painter.restore()

        painter.restore()

    def _draw_collapsing_beam(self, painter: QPainter, now: float):
        """Render classic comic collapsing industrial steel I-beam with rivets, hazard stripes, strain lines, and metric badge."""
        painter.save()
        cx = self._width / 2.0

        jitter_x = math.sin(now * 48.0) * 2.2
        jitter_y = math.cos(now * 56.0) * 1.8

        bw = 290.0
        bh = 34.0
        bx = cx - bw / 2.0 + jitter_x
        by = self._height - 48.0 + jitter_y

        # 1. Downward comic speed & strain lines
        painter.setPen(QPen(QColor(15, 23, 42, 160), 2.0, Qt.SolidLine))
        for line_offset in (-120, -80, -40, 0, 40, 80, 120):
            lx = cx + line_offset + jitter_x * 0.5
            painter.drawLine(int(lx), int(by - 26), int(lx), int(by - 6))

        # 2. Steel I-Beam Flanges and Web
        # Top Flange
        top_rect = QRectF(bx, by, bw, 8.0)
        grad_top = QLinearGradient(bx, by, bx, by + 8.0)
        grad_top.setColorAt(0.0, QColor("#64748B"))
        grad_top.setColorAt(1.0, QColor("#334155"))
        painter.setPen(QPen(QColor("#0F172A"), 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.setBrush(grad_top)
        painter.drawRoundedRect(top_rect, 2.0, 2.0)

        # Central Web Plate
        web_rect = QRectF(bx + 12.0, by + 8.0, bw - 24.0, 18.0)
        grad_web = QLinearGradient(bx, by + 8.0, bx, by + 26.0)
        grad_web.setColorAt(0.0, QColor("#1E293B"))
        grad_web.setColorAt(0.5, QColor("#334155"))
        grad_web.setColorAt(1.0, QColor("#0F172A"))
        painter.setBrush(grad_web)
        painter.drawRect(web_rect)

        # Diagonal Caution Hazard Stripes in central span (Industrial yellow/black)
        hazard_x = cx - 55.0 + jitter_x
        hazard_w = 110.0
        hazard_rect = QRectF(hazard_x, by + 8.0, hazard_w, 18.0)
        painter.save()
        painter.setClipRect(hazard_rect)
        painter.setPen(Qt.NoPen)
        painter.fillRect(hazard_rect, QColor("#FACC15"))
        painter.setBrush(QColor("#0F172A"))
        stripe_w = 10.0
        for sx in range(int(hazard_x - 30), int(hazard_x + hazard_w + 30), 20):
            poly = QPolygonF([
                QPointF(sx, by + 8.0),
                QPointF(sx + stripe_w, by + 8.0),
                QPointF(sx + stripe_w - 18.0, by + 26.0),
                QPointF(sx - 18.0, by + 26.0)
            ])
            painter.drawPolygon(poly)
        painter.restore()

        # Industrial Rivets along left and right web spans
        painter.setPen(QPen(QColor("#0F172A"), 1.5))
        painter.setBrush(QColor("#94A3B8"))
        for rx in (bx + 24, bx + 48, bx + 72, bx + bw - 72, bx + bw - 48, bx + bw - 24):
            painter.drawEllipse(QPointF(rx + jitter_x, by + 17.0), 3.0, 3.0)
            painter.fillRect(QRectF(rx + jitter_x - 1, by + 15.5, 1.5, 1.5), QColor("#FFFFFF"))

        # Stress fracture crack in center
        crack_pen = QPen(QColor("#0F172A"), 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(crack_pen)
        painter.drawPolyline([
            QPointF(cx - 10 + jitter_x, by + 2),
            QPointF(cx - 3 + jitter_x, by + 12),
            QPointF(cx + 4 + jitter_x, by + 20),
            QPointF(cx + 1 + jitter_x, by + 30)
        ])

        # Bottom Flange
        bot_rect = QRectF(bx, by + 26.0, bw, 8.0)
        grad_bot = QLinearGradient(bx, by + 26.0, bx, by + 34.0)
        grad_bot.setColorAt(0.0, QColor("#475569"))
        grad_bot.setColorAt(1.0, QColor("#1E293B"))
        painter.setPen(QPen(QColor("#0F172A"), 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.setBrush(grad_bot)
        painter.drawRoundedRect(bot_rect, 2.0, 2.0)

        # 3. Spider-Man's Gloved Hands Bracing Under the Beam
        hand_w, hand_h = 24.0, 16.0
        for hx in (cx - 44.0 + jitter_x * 0.5, cx + 20.0 + jitter_x * 0.5):
            painter.setPen(QPen(QColor("#0F172A"), 2.0))
            painter.setBrush(QColor("#DC2626"))
            painter.drawRoundedRect(QRectF(hx, by + 31.0, hand_w, hand_h), 5.0, 5.0)
            painter.setPen(QPen(QColor("#0F172A"), 1.2))
            painter.drawLine(int(hx + 6), int(by + 32), int(hx + 6), int(by + 44))
            painter.drawLine(int(hx + 12), int(by + 32), int(hx + 12), int(by + 45))
            painter.drawLine(int(hx + 18), int(by + 32), int(hx + 18), int(by + 44))
            painter.drawLine(int(hx + 2), int(by + 37), int(hx + hand_w - 2), int(by + 37))

        # 4. Falling Crumbling Rubble & Concrete Pebbles
        for p in self._rubble_particles:
            painter.setPen(QPen(QColor("#0F172A"), 1.0))
            painter.setBrush(QColor(p["color"]))
            painter.drawEllipse(QPointF(p["x"], p["y"]), p["size"] / 2.0, p["size"] / 2.0)

        # 5. Straining Sweat Beads (💦) Flying Outward
        sweat_pen = QPen(QColor("#0284C7"), 1.5)
        sweat_brush = QColor("#38BDF8")
        painter.setPen(sweat_pen)
        painter.setBrush(sweat_brush)
        painter.drawEllipse(QPointF(cx - 72.0 + jitter_x, by + 44.0), 4.5, 3.2)
        painter.drawEllipse(QPointF(cx - 88.0 + jitter_x, by + 36.0), 3.5, 2.5)
        painter.drawEllipse(QPointF(cx + 72.0 + jitter_x, by + 44.0), 4.5, 3.2)
        painter.drawEllipse(QPointF(cx + 88.0 + jitter_x, by + 36.0), 3.5, 2.5)

        # 6. High-Load Metric Badge Floating Above Beam
        badge_text = f"🔥 HEAVY LOAD | CPU: {int(self._heavy_cpu)}%   RAM: {int(self._heavy_ram)}%"
        badge_font = QFont("Impact", 11)
        if not badge_font.exactMatch():
            badge_font = QFont("Arial Black", 10)
        badge_font.setBold(True)
        painter.setFont(badge_font)
        fm = QFontMetrics(badge_font)
        bw_text = fm.horizontalAdvance(badge_text) + 26.0
        bh_badge = 26.0
        badge_rect = QRectF(cx - bw_text / 2.0 + jitter_x, by - 32.0, bw_text, bh_badge)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 90))
        painter.drawRoundedRect(badge_rect.translated(2.0, 2.0), 13.0, 13.0)

        grad_badge = QLinearGradient(badge_rect.left(), badge_rect.top(), badge_rect.right(), badge_rect.bottom())
        grad_badge.setColorAt(0.0, QColor("#7F1D1D"))
        grad_badge.setColorAt(1.0, QColor("#991B1B"))
        painter.setBrush(grad_badge)
        painter.setPen(QPen(QColor("#EF4444"), 1.8))
        painter.drawRoundedRect(badge_rect, 13.0, 13.0)

        painter.setPen(QColor("#FEF2F2"))
        painter.drawText(badge_rect, Qt.AlignCenter, badge_text)

        painter.restore()

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
        # Position relative to Spider-Man's head / squiggles / collapsing beam
        extra_lift = (45.0 if self._heavy_load_active else 0.0) + (30.0 if self._spider_sense_active else 0.0)
        inverted = self.is_inverted()
        if inverted:
            cy = 85.0 + float_y + extra_lift
            bx = cx - bw / 2.0
            by = cy
        else:
            cy = self._height - 65.0 + float_y - extra_lift
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

        # Pointer tail pointing towards Spider-Man's head
        tail_path = QPainterPath()
        if inverted:
            tail_p1 = QPointF(cx - 8.0, by + 1.0)
            tail_p2 = QPointF(cx + 8.0, by + 1.0)
            tail_tip = QPointF(cx - 2.0, by - 12.0)
        else:
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

    def _draw_charging_indicator(self, painter: QPainter, now: float):
        """Render stylish yellow-colored battery indicator floating right above/below head."""
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        cx = self._width / 2.0
        hover_y = math.sin(now * 3.5) * 2.0

        inverted = self.is_inverted()
        badge_cy = 40.0 + hover_y

        # Order requested: 1st Flash (⚡), 2nd Battery Percentage (94%), 3rd Battery 3-part indicator (🔋)
        text_str = f"{self._battery_percent}%"
        pct_font = QFont("Segoe UI", 10, QFont.Bold)
        if not pct_font.exactMatch():
            pct_font = QFont("Arial", 10, QFont.Bold)
        fm = QFontMetrics(pct_font)
        text_w = float(fm.horizontalAdvance(text_str))

        bolt_w = 9.0
        spacing_bolt_text = 5.0
        spacing_text_bat = 6.0
        bat_w = 20.0
        bat_h = 13.0
        nub_w = 2.5
        pad_x = 12.0  # Equal symmetric padding on both left and right

        content_w = bolt_w + spacing_bolt_text + text_w + spacing_text_bat + bat_w + nub_w
        bw = content_w + pad_x * 2.0
        bh = 28.0

        bx = cx - bw / 2.0
        by = badge_cy - bh / 2.0

        # 1. Subtle electric yellow ambient glow
        glow_pen = QPen(QColor(255, 230, 0, 50), 5.0)
        painter.setPen(glow_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(QRectF(bx, by, bw, bh), 14.0, 14.0)

        # 2. Sleek dark charcoal capsule background with vibrant yellow border
        badge_rect = QRectF(bx, by, bw, bh)
        painter.setPen(QPen(QColor("#FFE600"), 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.setBrush(QColor(16, 20, 26, 235))
        painter.drawRoundedRect(badge_rect, 14.0, 14.0)

        # 3. Item 1: Comic Sharp Lightning Bolt (⚡) in bright golden-yellow
        bolt_x = bx + pad_x
        bolt_y = by + 6.0
        bolt_poly = QPolygonF([
            QPointF(bolt_x + 5.0, bolt_y),
            QPointF(bolt_x, bolt_y + 8.5),
            QPointF(bolt_x + 4.5, bolt_y + 8.5),
            QPointF(bolt_x + 1.5, bolt_y + 16.0),
            QPointF(bolt_x + 9.0, bolt_y + 6.5),
            QPointF(bolt_x + 5.0, bolt_y + 6.5),
        ])
        painter.setPen(QPen(QColor("#FFE600"), 1.0))
        painter.setBrush(QColor("#FFE600"))
        painter.drawPolygon(bolt_poly)

        # 4. Item 2: Battery Percentage Number (e.g. 94%) in bold yellow
        text_x = bolt_x + bolt_w + spacing_bolt_text
        painter.setFont(pct_font)
        painter.setPen(QColor("#FFE600"))
        text_rect = QRectF(text_x, by, text_w + 2.0, bh)
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, text_str)

        # 5. Item 3: Battery 3-part indicator (🔋) at the very right
        bat_x = text_x + text_w + spacing_text_bat
        bat_y = by + (bh - bat_h) / 2.0
        painter.setPen(QPen(QColor("#FFE600"), 1.6))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(QRectF(bat_x, bat_y, bat_w, bat_h), 2.5, 2.5)

        # Battery terminal nub
        painter.fillRect(QRectF(bat_x + bat_w, by + (bh - 6.0) / 2.0, nub_w, 6.0), QColor("#FFE600"))

        # Animated 3-segment fill in yellow
        filled_cells = max(1, min(3, (self._battery_percent + 15) // 35))
        for c in range(filled_cells):
            cx_cell = bat_x + 2.5 + c * 5.3
            painter.fillRect(QRectF(cx_cell, bat_y + 2.5, 3.8, bat_h - 5.0), QColor("#FFE600"))


        # 6. Little electric sparkles (✦)
        spark_alpha = int(160 + 80 * math.sin(now * 7.0))
        painter.setPen(QColor(255, 230, 0, spark_alpha))
        painter.setFont(QFont("Segoe UI Symbol", 8))
        painter.drawText(QPointF(bx - 4.0, by + 5.0), "✦")
        painter.drawText(QPointF(bx + bw - 2.0, by + bh + 3.0), "✦")

        painter.restore()

