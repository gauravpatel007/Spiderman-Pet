"""Keep tests off the user's desktop and out of their saved preferences."""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.bootstrap import ensure_site_packages
ensure_site_packages()

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["APPDATA"] = str(ROOT / "build" / "test-user-data")

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def clean_test_settings():
    """Ensure every test runs with clean default settings, preventing cross-test pollution."""
    import warnings
    from services.settings_service import SettingsService
    s = SettingsService.get_instance()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        try:
            s.setting_changed.disconnect()
        except Exception:
            pass
        try:
            s.settings_reloaded.disconnect()
        except Exception:
            pass
    s.reset_to_defaults()
    yield
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        try:
            s.setting_changed.disconnect()
        except Exception:
            pass
        try:
            s.settings_reloaded.disconnect()
        except Exception:
            pass
    s.reset_to_defaults()
