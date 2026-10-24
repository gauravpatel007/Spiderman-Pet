"""
🕷️ SPIDER-BUDDY
Native Interactive Desktop Companion for Windows

Entry point script.
"""
import sys
import PySide6
import os

# Ensure package roots and dependencies are discoverable
current_dir = os.path.dirname(os.path.abspath(__file__))
try:
    os.chdir(current_dir)
except Exception:
    pass
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from app.bootstrap import bootstrap_environment
bootstrap_environment()

import signal
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from app.application import SpiderBuddyApp


def main() -> int:
    """Main application entry point."""
    import ctypes
    from PySide6.QtGui import QIcon
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SpiderBuddy.Companion.1.0")
    except Exception:
        pass

    qapp = QApplication(sys.argv)
    qapp.setApplicationName("SpiderBuddy")
    qapp.setApplicationDisplayName("")
    qapp.setOrganizationName("SpiderBuddy")

    # Set application top-left icon: only red spiderman face
    icon_path = os.path.join(current_dir, "assets", "icons", "spiderman_face.png")
    if not os.path.exists(icon_path):
        icon_path = os.path.join(current_dir, "assets", "icons", "spider.ico")
    if os.path.exists(icon_path):
        qapp.setWindowIcon(QIcon(icon_path))

    # Periodic timer to allow Python interpreter to catch Ctrl+C on Windows
    # Signal callbacks only set a flag: Qt cleanup must run outside a signal
    # handler, on the next event-loop tick (including Ctrl+Break on Windows).
    exit_requested = False

    def request_exit(signum, frame):
        nonlocal exit_requested
        exit_requested = True

    signals = [signal.SIGINT, signal.SIGTERM]
    if hasattr(signal, "SIGBREAK"):
        signals.append(signal.SIGBREAK)
    previous = {sig: signal.signal(sig, request_exit) for sig in signals}
    sig_timer = QTimer(qapp)
    spider_buddy = None
    try:
        spider_buddy = SpiderBuddyApp(qapp)
        sig_timer.timeout.connect(lambda: spider_buddy.shutdown() if exit_requested else None)
        sig_timer.start(100)
        spider_buddy.startup()
        if exit_requested:
            return 0
        return qapp.exec()
    finally:
        sig_timer.stop()
        if spider_buddy is not None:
            spider_buddy.shutdown()
        for sig, handler in previous.items():
            signal.signal(sig, handler)


if __name__ == "__main__":
    sys.exit(main())
