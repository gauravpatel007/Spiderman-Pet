"""Alpha hit testing in the rendered sprite's logical coordinate system."""
from typing import Optional
import re
from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QImage, QPixmap, QRegion


class HitTestManager:
    def __init__(self, alpha_threshold: int = 20):
        self.alpha_threshold = max(1, min(255, alpha_threshold))

    def is_point_inside_rect(self, point: QPoint, char_rect: QRect) -> bool:
        return char_rect.contains(point)

    def is_pixel_opaque(self, point: QPoint, char_rect: QRect,
                        frame_pixmap: Optional[QPixmap]) -> bool:
        if not char_rect.contains(point) or char_rect.isEmpty():
            return False
        if frame_pixmap is None or frame_pixmap.isNull():
            return False
        image = frame_pixmap.toImage()
        x = int((point.x() - char_rect.x()) * image.width() / char_rect.width())
        y = int((point.y() - char_rect.y()) * image.height() / char_rect.height())
        return image.pixelColor(x, y).alpha() >= self.alpha_threshold

    def opaque_region(self, image: QImage) -> QRegion:
        """Build a logical-pixel input region, preserving holes in the sprite."""
        rgba = image.convertToFormat(QImage.Format_RGBA8888)
        pixels = bytes(rgba.constBits())
        stride = rgba.bytesPerLine()
        region = QRegion()
        width = rgba.width()
        opaque_runs = re.compile(b'[' + re.escape(bytes([self.alpha_threshold])) + b'-\xff]+')
        for y in range(rgba.height()):
            row = y * stride
            alpha = pixels[row + 3:row + width * 4:4]
            for run in opaque_runs.finditer(alpha):
                region |= QRegion(QRect(run.start(), y, run.end() - run.start(), 1))
        return region
