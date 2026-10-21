"""Noninteractive, tightly bounded web strand in desktop logical coordinates."""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QRegion
from PySide6.QtWidgets import QWidget


class WebOverlay(QWidget):
    def __init__(self, pet, movement):
        super().__init__(pet, Qt.Tool | Qt.FramelessWindowHint |
                         Qt.WindowStaysOnTopHint | Qt.WindowTransparentForInput |
                         Qt.WindowDoesNotAcceptFocus)
        self.pet = pet
        self.movement = movement
        self.points = None
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.NoFocus)

    def set_strand(self, points):
        self.points = points
        if points is None or not self.pet.isVisible():
            self.hide()
            return
        a, b = (QPointF(*point) for point in points)
        box = QRectF(a, b).normalized().adjusted(-3, -3, 3, 3).toAlignedRect()
        self.setGeometry(box)
        self.setWindowOpacity(self.pet.windowOpacity())
        self.show()
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
        painter = QPainter(self)
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        painter.fillRect(self.rect(), Qt.transparent)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

        if not self.points:
            painter.end()
            return
        painter.setRenderHint(QPainter.Antialiasing)
        allowed = QRegion()
        for area in self.movement.regions:
            allowed |= QRegion(area.translated(-self.x(), -self.y()))
        painter.setClipRegion(allowed)
        painter.setPen(QPen(QColor(235, 240, 255, 215), 1.5))
        a, b = (QPointF(x-self.x(), y-self.y()) for x, y in self.points)
        painter.drawLine(a, b)
