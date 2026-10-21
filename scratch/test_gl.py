import os
import sys

sys.path.insert(0, os.path.abspath("."))
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu --disable-gpu-compositing --use-gl=disabled --disable-direct-composition --disable-direct-composition-video-overlays --disable-features=CalculateNativeWinOcclusion,WindowOcclusionCalculation,MrcMultiplaneOverlay --disable-backgrounding-occluded-windows"

from PySide6.QtWidgets import QApplication
from ui.web_window import WebMainWindow
from core.character_manager import CharacterManager

app = QApplication.instance() or QApplication([])
char_mgr = CharacterManager()
win = WebMainWindow(character_mgr=char_mgr)
print("Instantiated!")
win.stop()
print("Clean exit!")
