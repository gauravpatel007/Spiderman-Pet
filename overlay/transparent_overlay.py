"""Small alpha-shaped desktop window with DPI-aware rendering and input."""
from collections import OrderedDict
import ctypes
from ctypes import wintypes
import math
import sys
from typing import Optional

from PySide6.QtCore import QEvent, QPointF, QPoint, QRect, QSize, Qt, Signal, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QPolygonF, QPixmap, QRegion, QTransform
from PySide6.QtWidgets import QApplication, QWidget

from .hit_test_manager import HitTestManager

if sys.platform == 'win32':
    _screen_to_client = ctypes.windll.user32.ScreenToClient
    _screen_to_client.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
    _screen_to_client.restype = wintypes.BOOL


class TransparentOverlay(QWidget):
    clicked = Signal()
    double_clicked = Signal()
    drag_started = Signal(QPoint, QPoint)
    drag_moved = Signal(QPoint)
    drag_ended = Signal()
    context_menu_requested = Signal(QPoint)
    render_size_changed = Signal(int, int)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.hit_test = HitTestManager()
        self._current_frame = None
        self._rendered = QPixmap()
        self._input_region = QRegion()
        self._cache = OrderedDict()
        self._char_height = 200
        self._rotation = 0.0
        self._pose_rotation = 0.0
        self._reading = False
        self._is_low_battery = False
        self._battery_percent = 100
        self._glitch_active = False
        self._glitch_frame = 0
        self._glitch_timer = QTimer(self)
        self._glitch_timer.setInterval(40)
        self._glitch_timer.timeout.connect(self._on_glitch_frame)
        self._glitch_stop_timer = QTimer(self)
        self._glitch_stop_timer.setSingleShot(True)
        self._glitch_stop_timer.timeout.connect(self._stop_glitch)
        self._comic_effects = None
        self._spider_sense_active = False
        self._spider_sense_timer = QTimer(self)
        self._spider_sense_timer.setSingleShot(True)
        self._spider_sense_timer.timeout.connect(self._stop_spider_sense)
        self._opacity = 1.0
        self._click_through = False
        self._pressed = False
        self._is_dragging = False
        self._double_click = False
        self._drag_start_pos = QPoint()
        self._press_global = QPoint()
        self._screen_window = None
        self._click_timer = QTimer(self)
        self._click_timer.setSingleShot(True)
        self._click_timer.timeout.connect(self.clicked.emit)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint |
                            Qt.Tool | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.NoFocus)
        self.setMouseTracking(True)
        self.resize(200, 200)
        self._apply_input_region()

    def set_character_height(self, height: int):
        self._char_height = max(80, min(500, int(height)))
        self._refresh_render()

    def set_rotation(self, degrees: float):
        if math.isfinite(degrees):
            self._rotation = float(degrees) % 360
            self._refresh_render()

    def set_reading(self, reading):
        if self._reading != bool(reading):
            self._reading = bool(reading)
            self._cache.clear()
            self._refresh_render()

    def set_low_battery(self, is_low: bool, percent: int = 12):
        changed = (self._is_low_battery != bool(is_low) or self._battery_percent != percent)
        self._is_low_battery = bool(is_low)
        self._battery_percent = percent
        if changed:
            self.update()

    def set_comic_effects(self, comic_effects):
        """Attach companion comic effects overlay for speech bubbles & spider sense."""
        self._comic_effects = comic_effects

    def show_speech_bubble(self, text: str, duration_ms: int = 2200, style: str = "comic"):
        """Display animated pop-up comic dialogue bubble if enabled."""
        from services.settings_service import get_settings
        if not get_settings().get('behavior.enable_comic_bubbles', True):
            return
        if hasattr(self, '_comic_effects') and self._comic_effects:
            self._comic_effects.show_bubble(text, duration_ms, style)

    def trigger_spider_sense(self, duration_ms: int = 750):
        """⚡ Trigger Spider-Sense squiggles and eye corona if enabled."""
        from services.settings_service import get_settings
        if not get_settings().get('behavior.enable_spider_sense_dodging', True):
            return
        self._spider_sense_active = True
        self._spider_sense_timer.start(duration_ms)
        if hasattr(self, '_comic_effects') and self._comic_effects:
            self._comic_effects.trigger_spider_sense(duration_ms)
        self.update()

    def _stop_spider_sense(self):
        self._spider_sense_active = False
        self.update()

    def trigger_suit_glitch(self, duration_ms: int = 550):
        """Apply temporary chromatic aberration RGB split glitch shader to mimic multiverse glitch."""
        self._glitch_active = True
        self._glitch_frame = 0
        self.clearMask()
        if not self._glitch_timer.isActive():
            self._glitch_timer.start()
        self._glitch_stop_timer.start(duration_ms)
        self.update()

    def _on_glitch_frame(self):
        self._glitch_frame += 1
        self.update()

    def _stop_glitch(self):
        self._glitch_active = False
        self._glitch_timer.stop()
        self._apply_input_region()
        self.update()

    def set_pose_rotation(self, degrees):
        # Rotate within the existing canvas so physics dimensions stay stable.
        angle = round(float(degrees)/2)*2
        if angle != self._pose_rotation:
            self._pose_rotation = angle
            self._refresh_render()

    def set_character_opacity(self, opacity: float):
        self._opacity = max(0.1, min(1.0, float(opacity)))
        self.setWindowOpacity(self._opacity)

    def set_click_through(self, enabled: bool):
        """Optional full click-through; normal mode uses the sprite silhouette."""
        self._click_through = bool(enabled)
        if enabled:
            self._cancel_gesture()
        visible = self.isVisible()
        self.setWindowFlag(Qt.WindowTransparentForInput, self._click_through)
        if visible:
            self.show()
        self._apply_input_region()

    def set_frame(self, pixmap: QPixmap):
        if pixmap.isNull():
            return
        self._current_frame = pixmap
        self._refresh_render()

    def _refresh_render(self):
        source = self._current_frame
        if source is None or source.isNull():
            return
        dpr = max(1.0, self.devicePixelRatioF())
        key = (source.cacheKey(), self._char_height, self._rotation, self._pose_rotation, self._reading, round(dpr, 4))
        if key in self._cache:
            rendered, region, logical = self._cache[key]
            self._cache.move_to_end(key)
        else:
            # Scale at physical resolution, then tag with DPR for Qt painting.
            height = max(1, round(self._char_height * dpr))
            if self._reading:
                source = source.copy()
                painter = QPainter(source)
                painter.setRenderHint(QPainter.Antialiasing)
                painter.scale(source.width()/512, source.height()/512)

                # 1. Open Comic Book in Spider-Man's hands
                # Comic book spine & covers
                painter.setPen(QPen(QColor('#1E2530'), 2))
                painter.setBrush(QColor('#C62828'))  # Deep red cover left page
                painter.drawPolygon(QPolygonF([QPointF(168, 340), QPointF(256, 356), QPointF(256, 442), QPointF(168, 426)]))
                painter.setBrush(QColor('#1565C0'))  # Royal blue cover right page
                painter.drawPolygon(QPolygonF([QPointF(256, 356), QPointF(344, 340), QPointF(344, 426), QPointF(256, 442)]))

                # Comic inner pages (vintage off-white paper)
                painter.setPen(QPen(QColor('#F9F6EE'), 1.5))
                painter.drawPolyline([QPointF(174, 344), QPointF(256, 358), QPointF(338, 344)])
                painter.drawPolyline([QPointF(174, 422), QPointF(256, 438), QPointF(338, 422)])

                # Comic book colorful panels & dialogue squiggles
                painter.setPen(QPen(QColor('#FFE082'), 1.5))
                painter.drawLine(180, 362, 246, 374)
                painter.drawLine(266, 374, 332, 362)
                # Illustrated comic panels
                painter.setPen(QPen(QColor('#222222'), 1))
                painter.setBrush(QColor('#FFE082'))
                painter.drawRect(184, 378, 28, 22)
                painter.setBrush(QColor('#EF5350'))
                painter.drawRect(218, 381, 28, 22)
                painter.setBrush(QColor('#42A5F5'))
                painter.drawRect(266, 381, 28, 22)
                painter.setBrush(QColor('#AB47BC'))
                painter.drawRect(300, 378, 28, 22)

                # Mini Spider-symbol emblem on comic cover page
                painter.setPen(QPen(QColor('#FFFFFF'), 1.5))
                painter.drawEllipse(204, 408, 10, 10)
                painter.drawEllipse(298, 408, 10, 10)

                # 2. Stylish Reading Glasses over Spider-Man's eye lenses
                # Tortoiseshell / dark rimmed frames with gold bridge
                glasses_rim_pen = QPen(QColor('#1A1D20'), 3.5)
                painter.setPen(glasses_rim_pen)

                # Left Glass Lens (tinted anti-reflective glass + frame)
                painter.setBrush(QColor(160, 225, 255, 95))
                painter.drawRoundedRect(QRect(196, 172, 48, 34), 9, 9)

                # Right Glass Lens (tinted anti-reflective glass + frame)
                painter.drawRoundedRect(QRect(268, 172, 48, 34), 9, 9)

                # Connecting Nose Bridge
                painter.setPen(QPen(QColor('#D4AF37'), 3))  # Gold wire bridge
                painter.drawLine(244, 185, 268, 185)

                # Temple arms extending back to the ears
                painter.setPen(QPen(QColor('#1A1D20'), 2.5))
                painter.drawLine(196, 182, 172, 177)  # Left arm
                painter.drawLine(316, 182, 340, 177)  # Right arm

                # Glass lens glare reflections (white diagonal highlights)
                painter.setPen(QPen(QColor(255, 255, 255, 190), 2))
                painter.drawLine(202, 178, 214, 178)
                painter.drawLine(202, 183, 208, 183)
                painter.drawLine(274, 178, 286, 178)
                painter.drawLine(274, 183, 280, 183)

                painter.end()
            rendered = source.scaledToHeight(height, Qt.SmoothTransformation)
            rendered.setDevicePixelRatio(1)
            if self._pose_rotation:
                canvas = QPixmap(rendered.size())
                canvas.fill(Qt.transparent)
                rotated = rendered.transformed(QTransform().rotate(self._pose_rotation), Qt.SmoothTransformation)
                rotated = rotated.scaled(canvas.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                painter = QPainter(canvas)
                painter.drawPixmap((canvas.width()-rotated.width())//2,
                                   (canvas.height()-rotated.height())//2, rotated)
                painter.end()
                rendered = canvas
            if self._rotation:
                rendered = rendered.transformed(QTransform().rotate(self._rotation), Qt.SmoothTransformation)
            logical = QSize(max(1, round(rendered.width()/dpr)), max(1, round(rendered.height()/dpr)))
            logical_image = rendered.toImage().scaled(logical, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            region = self.hit_test.opaque_region(logical_image)
            rendered.setDevicePixelRatio(dpr)
            self._cache[key] = (rendered, region, logical)
            # Bound memory use even at 200% DPI; no full-screen backing image.
            while len(self._cache) > 24:
                self._cache.popitem(last=False)
        self._rendered = rendered
        self._input_region = region
        if self.size() != logical:
            self.resize(logical)
            self.render_size_changed.emit(logical.width(), logical.height())
        self._apply_input_region()
        self.update()

    def _apply_input_region(self):
        # Native window shaping excludes transparent pixels from hit testing
        # across process boundaries. HTTRANSPARENT alone cannot guarantee that.
        # An empty Qt mask clears masking, so use an off-window region instead.
        region = self._input_region
        self.setMask(region if not region.isEmpty() else QRegion(QRect(-2, -2, 1, 1)))

    def _accepts(self, point):
        return not self._click_through and self._input_region.contains(point)

    def update_position(self, x: int, y: int):
        self.move(int(x), int(y))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        painter.fillRect(self.rect(), Qt.transparent)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.Antialiasing)

        if self._rendered.isNull():
            painter.end()
            return

        if self._glitch_active:
            import random
            # Spider-Verse suit flickering opacity
            flicker_opacity = random.choice([0.45, 0.75, 0.9, 1.0, 0.35])
            w, h = self.width(), self.height()
            jitter_x = random.randint(-5, 5)

            # Spider-Verse chromatic aberration & horizontal slice displacement
            num_slices = 5
            slice_h = max(1, h // num_slices)
            for i in range(num_slices):
                sy = i * slice_h
                sh = min(slice_h, h - sy)
                sx_offset = random.choice([-8, -5, -2, 0, 3, 6, 8]) + jitter_x
                # Cyan/Blue shift pass (chromatic aberration - left)
                painter.setOpacity(0.6 * flicker_opacity)
                painter.drawPixmap(sx_offset - 6, sy, self._rendered, 0, sy, w, sh)
                # Red/Magenta shift pass (chromatic aberration - right)
                painter.setOpacity(0.6 * flicker_opacity)
                painter.drawPixmap(sx_offset + 6, sy, self._rendered, 0, sy, w, sh)
                # Main sprite slice
                painter.setOpacity(flicker_opacity)
                painter.drawPixmap(sx_offset, sy, self._rendered, 0, sy, w, sh)

            # Digital glitch artifact blocks (Spider-Verse neon flicker)
            for _ in range(random.randint(3, 6)):
                gx = random.randint(6, max(8, w - 28))
                gy = random.randint(6, max(8, h - 20))
                gw = random.randint(12, 34)
                gh = random.randint(3, 8)
                glitch_color = random.choice([
                    QColor(0, 240, 255, 190),   # Neon Cyan
                    QColor(255, 0, 110, 190),   # Neon Magenta
                    QColor(255, 235, 0, 190),   # Neon Yellow
                    QColor(255, 255, 255, 210), # Glitch White
                ])
                painter.fillRect(QRect(gx, gy, gw, gh), glitch_color)

            painter.setOpacity(1.0)
        else:
            painter.drawPixmap(0, 0, self._rendered)

        # If Spider-Sense is active, draw subtle golden/crimson tingle aura on character mask
        if self._spider_sense_active:
            w, h = self.width(), self.height()
            painter.save()
            head_cx = w / 2.0
            head_cy = h * 0.26
            aura_pen = QPen(QColor(255, 230, 0, 175), 2.5)
            painter.setPen(aura_pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QPointF(head_cx, head_cy), w * 0.22, w * 0.18)
            painter.restore()

        # If low battery, draw exhausted badge & comic panting/sweat drops
        if self._is_low_battery:
            # Low battery indicator near top
            bw, bh = 34, 14
            bx = max(4, (self.width() - bw) // 2)
            by = 4

            # Subtle dark pill background
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(10, 14, 22, 190))
            painter.drawRoundedRect(QRect(bx - 4, by - 2, bw + 8, bh + 4), 6, 6)

            # Battery outline (Red glowing)
            painter.setPen(QPen(QColor('#FF3B5C'), 1.5))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(QRect(bx, by, bw - 4, bh), 2, 2)
            # Battery terminal nub
            painter.fillRect(QRect(bx + bw - 4, by + 4, 3, 6), QColor('#FF3B5C'))
            # Battery level fill (15% or less)
            fill_w = max(3, int((bw - 8) * (max(5, self._battery_percent) / 100)))
            painter.fillRect(QRect(bx + 2, by + 2, fill_w, bh - 4), QColor('#FF2D55'))

            # Exhausted comic sweat drops near mask (right side of head)
            painter.setPen(QPen(QColor('#64B5F6'), 1.5))
            painter.setBrush(QColor('#BBDEFB'))
            # Tear/sweat drop 1
            drop_x = min(self.width() - 16, int(self.width() * 0.72))
            drop_y = int(self.height() * 0.22)
            painter.drawEllipse(drop_x, drop_y, 5, 8)
            # Tear/sweat drop 2
            painter.drawEllipse(drop_x + 6, drop_y + 9, 4, 6)

        painter.end()

    def showEvent(self, event):
        super().showEvent(event)
        handle = self.windowHandle()
        if handle is not None and handle is not self._screen_window:
            handle.screenChanged.connect(self._screen_changed)
            self._screen_window = handle
        self._refresh_render()

    def _screen_changed(self, *args):
        self._cache.clear()
        self._refresh_render()

    def event(self, event):
        # Qt delivers this after a window crosses monitors or scaling changes.
        if event.type() == QEvent.DevicePixelRatioChange and hasattr(self, '_cache'):
            self._cache.clear()
            QTimer.singleShot(0, self._refresh_render)
        if event.type() == QEvent.UngrabMouse and getattr(self, '_pressed', False):
            self._cancel_gesture()
        return super().event(event)

    def nativeEvent(self, event_type, message):
        if sys.platform == 'win32':
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == 0x0021:  # WM_MOUSEACTIVATE / MA_NOACTIVATE
                return True, 3
            if msg.message == 0x0084:  # WM_NCHITTEST: physical screen coordinates
                x = ctypes.c_short(msg.lParam & 0xffff).value
                y = ctypes.c_short((msg.lParam >> 16) & 0xffff).value
                point = wintypes.POINT(x, y)
                if _screen_to_client(msg.hWnd, ctypes.byref(point)):
                    dpr = max(1.0, self.devicePixelRatioF())
                    local = QPoint(math.floor(point.x/dpr), math.floor(point.y/dpr))
                    return True, 1 if self._is_dragging or self._accepts(local) else -1
        return super().nativeEvent(event_type, message)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self._accepts(event.position().toPoint()):
            self._pressed = True
            self._double_click = False
            self._drag_start_pos = event.position().toPoint()
            self._press_global = event.globalPosition().toPoint()
            event.accept()
        else:
            event.ignore()

    def mouseMoveEvent(self, event):
        if not self._pressed or not event.buttons() & Qt.LeftButton:
            event.ignore()
            return
        global_pos = event.globalPosition().toPoint()
        if not self._is_dragging:
            distance = (global_pos - self._press_global).manhattanLength()
            if distance < QApplication.startDragDistance():
                event.accept()
                return
            self._click_timer.stop()
            self._is_dragging = True
            self.drag_started.emit(self._press_global, self._drag_start_pos)
        self.drag_moved.emit(global_pos)
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton or not self._pressed:
            event.ignore()
            return
        was_dragging = self._is_dragging
        self._pressed = False
        self._is_dragging = False
        if was_dragging:
            self.drag_ended.emit()
        elif not self._double_click and self._accepts(event.position().toPoint()):
            # Delay a single click so a double click does not also poke the pet.
            self._click_timer.start(QApplication.doubleClickInterval())
        self._double_click = False
        event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton and self._accepts(event.position().toPoint()):
            self._click_timer.stop()
            self._is_dragging = False
            self._pressed = False
            self._double_click = True
            self.double_clicked.emit()
            event.accept()
        else:
            event.ignore()

    def contextMenuEvent(self, event):
        if self._accepts(event.pos()):
            self._click_timer.stop()
            self.context_menu_requested.emit(event.globalPos())
            event.accept()
        else:
            event.ignore()

    def _cancel_gesture(self):
        self._click_timer.stop()
        dragging = self._is_dragging
        self._pressed = self._is_dragging = self._double_click = False
        if dragging:
            self.drag_ended.emit()

    def hideEvent(self, event):
        self._cancel_gesture()
        super().hideEvent(event)
