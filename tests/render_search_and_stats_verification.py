"""Test and capture screenshots of the new Command Palette (Ctrl+K) and Feature Search."""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from core.character_manager import CharacterManager
from ui.web_window import WebMainWindow
from services.companion_stats import CompanionStatsService

def main():
    os.environ["QT_QPA_PLATFORM"] = "windows"
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    char_mgr = CharacterManager()
    win = WebMainWindow(character_mgr=char_mgr)
    win.resize(1380, 840)
    win.show()

    stats_service = CompanionStatsService()
    win.reset_companion_stats_requested.connect(stats_service.reset_stats)

    artifact_dir = Path(r"C:\Users\Gaurav Patel\.gemini\antigravity\brain\3455a2ec-d2c9-4346-a48a-ffa1dfb1cfd3")
    out_palette = artifact_dir / "command_palette_search_verified.png"
    out_results = artifact_dir / "command_palette_results_verified.png"

    def wait_until_ready():
        def on_check(is_ready):
            if is_ready:
                # Open Command Palette via simulated click on Search Field
                win._run_js("""
                    const sf = document.querySelector('[data-framer-name="Search field"]');
                    if (sf) sf.click();
                """)
                QTimer.singleShot(800, capture_palette_open)
            else:
                QTimer.singleShot(300, wait_until_ready)

        win.web_view.page().runJavaScript(
            "Boolean(window.SpiderBuddy && document.getElementById('spider-command-palette'))",
            on_check
        )

    def capture_palette_open():
        pix = win.grab()
        pix.save(str(out_palette), "PNG")
        print(f"SAVED_PALETTE: {out_palette}")

        # Type "headphones" in search input to filter
        win._run_js("""
            const inp = document.getElementById('palette-input');
            if (inp) {
                inp.value = 'headphones';
                inp.dispatchEvent(new Event('input'));
            }
        """)
        QTimer.singleShot(800, capture_palette_filtered)

    def capture_palette_filtered():
        pix = win.grab()
        pix.save(str(out_results), "PNG")
        print(f"SAVED_RESULTS: {out_results}")

        # Verify stats reset method works cleanly
        stats_service.record_movement(100, 200)
        stats_service.record_web_swing()
        win.reset_companion_stats_requested.emit()
        assert stats_service._stats["distance_px"] == 0.0
        assert stats_service._stats["webs_shot"] == 0
        assert stats_service._stats["active_seconds"] == 0
        print("COMPANION_STATS_RESET_VERIFIED: PASS")

        win.stop()
        win.close()
        app.quit()

    QTimer.singleShot(1500, wait_until_ready)
    app.exec()

if __name__ == "__main__":
    main()
