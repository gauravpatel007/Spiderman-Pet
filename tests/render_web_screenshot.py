"""Capture screenshots of WebMainWindow at multiple sizes to verify responsive scaling."""
import os
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from core.character_manager import CharacterManager
from ui.web_window import WebMainWindow


def main():
    os.environ["QT_QPA_PLATFORM"] = "windows"
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    char_mgr = CharacterManager()
    win = WebMainWindow(character_mgr=char_mgr)
    win.resize(1380, 820)
    win.show()

    output_dir = Path("build/ui-review")
    output_dir.mkdir(parents=True, exist_ok=True)
    out_large = output_dir / "web_home_responsive_large.png"
    out_small = output_dir / "web_home_responsive_small.png"

    def capture_large():
        pix = win.grab()
        pix.save(str(out_large), "PNG")
        print(f"SAVED_LARGE: {out_large.resolve()}")

        # Now resize smaller to verify fluid responsive scaling
        win.resize(1120, 680)
        QTimer.singleShot(1500, capture_small)

    def capture_small():
        pix = win.grab()
        pix.save(str(out_small), "PNG")
        print(f"SAVED_SMALL: {out_small.resolve()}")
        win.stop()
        win.close()
        app.quit()

    QTimer.singleShot(2500, capture_large)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
