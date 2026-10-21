"""Runtime screen flicker & desktop application diagnostic (isolated instance)."""
import os
import sys
import time

current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from app.bootstrap import bootstrap_environment
bootstrap_environment()

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QApplication
from ui.web_window import WebMainWindow
from core.character_manager import CharacterManager

def run_diagnostic():
    print("--- STARTING DESKTOP APP & SCREEN FLICKER DIAGNOSTIC ---")
    qapp = QApplication(sys.argv)
    qapp.setApplicationName("SpiderBuddyIsolated")
    
    char_mgr = CharacterManager()
    mw = WebMainWindow(character_mgr=char_mgr)
    mw.show()
    
    print(f"Main window title: '{mw.windowTitle()}'")
    print(f"Main window flags: {mw.windowFlags()}")
    print(f"Is Main window StayOnTop: {bool(mw.windowFlags() & Qt.WindowStaysOnTopHint)}")
    print(f"Main window geometry: {mw.geometry().getRect()}")
    screen = qapp.primaryScreen()
    avail = screen.availableGeometry() if screen else None
    print(f"Primary screen availableGeometry (work area): {avail.getRect() if avail else 'N/A'}")
    
    # Check if main window overlaps or covers taskbar
    has_bug = False
    if avail and mw.geometry().bottom() > avail.bottom():
        print(f"❌ BUG: Main window bottom ({mw.geometry().bottom()}) exceeds available screen bottom ({avail.bottom()})! OVERLAPPING TASKBAR!")
        has_bug = True
    else:
        print(f"✅ PASSED: Main window bottom ({mw.geometry().bottom()}) is safely within available work area ({avail.bottom()}). TASKBAR IS FREE!")
        
    if bool(mw.windowFlags() & Qt.WindowStaysOnTopHint):
        print(f"❌ BUG: Main window has WindowStaysOnTopHint! Overriding all other desktop apps and taskbar!")
        has_bug = True
    else:
        print("✅ PASSED: Main window is a proper desktop application (WindowStaysOnTopHint is FALSE)!")
        
    mw.stop()
    mw.close()
    print("--- DIAGNOSTIC RESULT:", "FAILED" if has_bug else "ALL CHECKS PASSED", "---")

if __name__ == "__main__":
    run_diagnostic()
