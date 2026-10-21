"""Capture scrolled screenshots verifying Activities Tab and Desktop & Apps."""
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

    artifact_dir = Path(r"C:\Users\Gaurav Patel\.gemini\antigravity\brain\3455a2ec-d2c9-4346-a48a-ffa1dfb1cfd3")
    out_act_scroll = artifact_dir / "tab_activities_verified_scrolled.png"
    out_apps_scroll = artifact_dir / "tab_desktop_apps_verified_scrolled.png"

    def wait_until_ready():
        def on_check(is_ready):
            if is_ready:
                win._run_js("window.SpiderBuddy.switchTab('Activities')")
                QTimer.singleShot(1000, scroll_activities)
            else:
                QTimer.singleShot(300, wait_until_ready)

        win.web_view.page().runJavaScript(
            "Boolean(window.SpiderBuddy && document.getElementById('dashboard-activities-view'))",
            on_check
        )

    def scroll_activities():
        win._run_js("const c = document.querySelector('[data-framer-name=\"Main dashboard\"]') || document.querySelector('.framer-j703sm'); if (c) c.scrollTop = 550;")
        QTimer.singleShot(1000, capture_activities_scrolled)

    def capture_activities_scrolled():
        pix = win.grab()
        pix.save(str(out_act_scroll), "PNG")
        print(f"SAVED_ACT_SCROLL: {out_act_scroll}")

        win._run_js("window.SpiderBuddy.switchTab('Desktop & Apps')")
        QTimer.singleShot(1000, scroll_apps)

    def scroll_apps():
        win._run_js("const c = document.querySelector('[data-framer-name=\"Main dashboard\"]') || document.querySelector('.framer-j703sm'); if (c) c.scrollTop = 450;")
        QTimer.singleShot(1000, capture_apps_scrolled)

    def capture_apps_scrolled():
        pix = win.grab()
        pix.save(str(out_apps_scroll), "PNG")
        print(f"SAVED_APPS_SCROLL: {out_apps_scroll}")

        win.stop()
        win.close()
        app.quit()

    QTimer.singleShot(800, wait_until_ready)
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
