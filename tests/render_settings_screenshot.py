"""Capture screenshots of WebMainWindow Settings tab."""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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

    artifact_dir = Path(r"C:\Users\Gaurav Patel\.gemini\antigravity\brain\04bd7ceb-0066-4e3d-90a4-8a942f036bac")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    out_top = artifact_dir / "tab_settings_top.png"
    out_scrolled = artifact_dir / "tab_settings_scrolled.png"

    def wait_until_ready():
        def on_check(is_ready):
            if is_ready:
                print("BRIDGE_READY! Switching to Settings tab...")
                win._run_js("window.SpiderBuddy.switchTab('Settings')")
                QTimer.singleShot(1500, capture_top)
            else:
                QTimer.singleShot(300, wait_until_ready)

        win.web_view.page().runJavaScript(
            "Boolean(window.SpiderBuddy && document.getElementById('dashboard-settings-view'))",
            on_check
        )

    def capture_top():
        pix = win.grab()
        pix.save(str(out_top), "PNG")
        print(f"SAVED_SETTINGS_TOP: {out_top.resolve()}")

        # Scroll down
        win._run_js("""
            window.scrollTo(0, 600);
            document.documentElement.scrollTop = 600;
            document.body.scrollTop = 600;
            const c1 = document.querySelector('[data-framer-name="Dashboard content"]');
            if (c1) c1.scrollTop = 600;
            const c2 = document.querySelector('[data-framer-name="Main dashboard"]');
            if (c2) c2.scrollTop = 600;
            const c3 = document.querySelector('.framer-j703sm');
            if (c3) c3.scrollTop = 600;
            const c4 = document.querySelector('.framer-p2nqtm');
            if (c4) c4.scrollTop = 600;
            const c5 = document.querySelector('.framer-72rtr7');
            if (c5) c5.scrollTop = 600;
        """)
        QTimer.singleShot(1200, capture_scrolled)

    def capture_scrolled():
        pix = win.grab()
        pix.save(str(out_scrolled), "PNG")
        print(f"SAVED_SETTINGS_SCROLLED: {out_scrolled.resolve()}")

        win.stop()
        win.close()
        app.quit()

    QTimer.singleShot(800, wait_until_ready)
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
