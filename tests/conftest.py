"""Keep tests off the user's desktop and out of their saved preferences."""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.bootstrap import ensure_site_packages
ensure_site_packages()

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["APPDATA"] = str(ROOT / "build" / "test-user-data")

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])
