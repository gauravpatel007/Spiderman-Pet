"""Fit readable headphones to the crown silhouette, before sprite transforms."""
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QLinearGradient


def with_headphones(source):
    image = source.toImage()
    # Sample a small alpha silhouette; avoid scanning every full-resolution pixel.
    sample = image.scaledToHeight(128, Qt.SmoothTransformation)
    rows = []
    for y in range(sample.height()):
        runs, start = [], None
        for x in range(sample.width() + 1):
            opaque = x < sample.width() and sample.pixelColor(x, y).alpha() > 100
            if opaque and start is None:
                start = x
            elif not opaque and start is not None:
                runs.append((start, x))
                start = None
        rows.append(runs)
    occupied = [y for y, runs in enumerate(rows) if runs]
    if not occupied:
        return source
    top, bottom = occupied[0], occupied[-1]
    span = bottom - top + 1
    candidates = [run for runs in rows[top + int(span*.10):top + max(2, int(span*.28))]
                  for run in runs]
    if not candidates:
        return source
    left, right = max(candidates, key=lambda run: run[1] - run[0])
    scale = source.height() / sample.height()
    width = (right-left) * scale
    cx, crown = (left+right)*scale/2, top*scale
    result = source.copy()
    painter = QPainter(result)
    painter.setRenderHint(QPainter.Antialiasing)
    # Bright edge separates the dark padded band from both red and black suits.
    band = QRectF(cx-width*.52, crown-width*.035, width*1.04, width*.92)
    painter.setBrush(Qt.NoBrush)
    for color, thickness in [('#d6e5f4', .105), ('#151c29', .080), ('#f43f5e', .033)]:
        painter.setPen(QPen(QColor(color), max(2, width*thickness), Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(band, 0, 180*16)
    cup_w, cup_h = width*.22, width*.39
    for sign in (-1, 1):
        x, y = cx + sign*width*.51-cup_w/2, crown+width*.42
        shell = QRectF(x, y, cup_w, cup_h)
        gradient = QLinearGradient(x, y, x+cup_w, y+cup_h)
        gradient.setColorAt(0, QColor('#59677e'))
        gradient.setColorAt(1, QColor('#111827'))
        painter.setBrush(gradient)
        painter.setPen(QPen(QColor('#e5edf7'), max(2, width*.018)))
        painter.drawRoundedRect(shell, cup_w*.35, cup_w*.35)
        painter.setBrush(QColor('#ef294e'))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(shell.adjusted(cup_w*.22, cup_h*.15, -cup_w*.22, -cup_h*.25),
                                cup_w*.18, cup_w*.18)
        painter.setBrush(QColor('#67e8f9'))
        painter.drawEllipse(QRectF(x+cup_w*.36, y+cup_h*.79, cup_w*.28, cup_w*.12))
    painter.end()
    return result
