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

    def paintEvent(self, event):
        if not self.points:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        allowed = QRegion()
        for area in self.movement.regions:
            allowed |= QRegion(area.translated(-self.x(), -self.y()))
        painter.setClipRegion(allowed)
        painter.setPen(QPen(QColor(235, 240, 255, 215), 1.5))
        a, b = (QPointF(x-self.x(), y-self.y()) for x, y in self.points)
        painter.drawLine(a, b)
