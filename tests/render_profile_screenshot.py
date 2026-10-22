"""Capture visual verification screenshots of My Profile tab and Character Recycle Bin."""
import os
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from app.bootstrap import ensure_site_packages
ensure_site_packages()

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
    win.resize(1280, 820)
    win.show()

    artifact_dir = Path(r"C:\Users\Gaurav Patel\.gemini\antigravity\brain\ee50579e-fd9f-48a3-a584-ce19696653f7")
    artifact_dir.mkdir(parents=True, exist_ok=True)

    out_sidebar = artifact_dir / "my_profile_sidebar_tab.png"
    out_profile_overview = artifact_dir / "my_profile_overview_apple_design.png"
    out_profile_bin = artifact_dir / "my_profile_character_bin_tab.png"

    def wait_until_ready():
        def on_check(is_ready):
            if is_ready:
                print("BRIDGE_READY! Capturing Home/Characters with My Profile in sidebar...")
                QTimer.singleShot(1200, capture_sidebar)
            else:
                QTimer.singleShot(300, wait_until_ready)

        win.web_view.page().runJavaScript(
            "Boolean(window.SpiderBuddy && document.getElementById('dashboard-profile-view'))",
            on_check
        )

    def capture_sidebar():
        pix = win.grab()
        pix.save(str(out_sidebar), "PNG")
        print(f"SAVED_SIDEBAR: {out_sidebar.resolve()}")

        # Switch to Profile Tab
        win._run_js("window.SpiderBuddy.switchTab('Profile')")
        QTimer.singleShot(1200, capture_overview)

    def capture_overview():
        pix = win.grab()
        pix.save(str(out_profile_overview), "PNG")
        print(f"SAVED_PROFILE_OVERVIEW: {out_profile_overview.resolve()}")

        # Switch to Bin inner tab
        win._run_js("window.SpiderBuddy.switchProfileSegment('bin')")
        QTimer.singleShot(1000, capture_bin)

    def capture_bin():
        pix = win.grab()
        pix.save(str(out_profile_bin), "PNG")
        print(f"SAVED_PROFILE_BIN: {out_profile_bin.resolve()}")

        QTimer.singleShot(500, lambda: (win.close(), app.quit()))

    QTimer.singleShot(600, wait_until_ready)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
