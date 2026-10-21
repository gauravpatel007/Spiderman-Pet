"""Capture screenshots of WebMainWindow Activities and Characters tabs after confirming bridge is ready."""
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
    win.resize(1380, 840)
    win.show()

    output_dir = Path("build/ui-review")
    output_dir.mkdir(parents=True, exist_ok=True)
    out_act = output_dir / "web_activities_tab.png"
    out_char = output_dir / "web_characters_tab.png"
    out_act_small = output_dir / "web_activities_tab_small.png"

    def wait_until_ready():
        def on_check(is_ready):
            if is_ready:
                print("BRIDGE_READY! Switching to Activities tab...")
                win._run_js("window.SpiderBuddy.switchTab('Activities')")
                QTimer.singleShot(1200, capture_activities_large)
            else:
                QTimer.singleShot(300, wait_until_ready)

        win.web_view.page().runJavaScript(
            "Boolean(window.SpiderBuddy && document.getElementById('dashboard-activities-view'))",
            on_check
        )

    def capture_activities_large():
        pix = win.grab()
        pix.save(str(out_act), "PNG")
        print(f"SAVED_ACTIVITIES: {out_act.resolve()}")

        # Resize to small to verify responsive wrapping
        win.resize(1120, 680)
        QTimer.singleShot(1200, capture_activities_small)

    def capture_activities_small():
        pix = win.grab()
        pix.save(str(out_act_small), "PNG")
        print(f"SAVED_ACTIVITIES_SMALL: {out_act_small.resolve()}")

        # Switch to Characters tab
        win.resize(1380, 840)
        win._run_js("window.SpiderBuddy.switchTab('Characters')")
        QTimer.singleShot(1200, capture_characters)

    def capture_characters():
        pix = win.grab()
        pix.save(str(out_char), "PNG")
        print(f"SAVED_CHARACTERS: {out_char.resolve()}")

        win.stop()
        win.close()
        app.quit()

    QTimer.singleShot(800, wait_until_ready)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
