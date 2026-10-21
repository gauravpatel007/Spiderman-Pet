"""Test adding disable-gpu flags to bootstrap and verifying Qt still works."""
import os
import sys

sys.path.insert(0, os.path.abspath("."))
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu --disable-gpu-compositing --disable-direct-composition --disable-direct-composition-video-overlays --disable-features=CalculateNativeWinOcclusion,WindowOcclusionCalculation,MrcMultiplaneOverlay --disable-backgrounding-occluded-windows --enable-begin-frame-scheduling"
os.environ["QSG_RHI_BACKEND"] = "software"
os.environ["QT_QUICK_BACKEND"] = "software"

from app.bootstrap import bootstrap_environment
bootstrap_environment()

from PySide6.QtWidgets import QApplication
from ui.web_window import WebMainWindow
from core.character_manager import CharacterManager

app = QApplication.instance() or QApplication([])
char_mgr = CharacterManager()
win = WebMainWindow(character_mgr=char_mgr)
print("WebMainWindow instantiated successfully with software flags!")
win.stop()
print("WebMainWindow stopped cleanly!")
