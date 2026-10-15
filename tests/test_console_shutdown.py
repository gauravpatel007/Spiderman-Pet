"""Exercise the entry point's signal bridge in a fresh Qt process."""
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize("signal_name", ["SIGINT", "SIGTERM", "SIGBREAK"] if os.name == "nt" else ["SIGINT", "SIGTERM"])
def test_console_signal_cleans_up(signal_name, tmp_path):
    root = Path(__file__).resolve().parents[1]
    script = r'''
import signal
import uuid
import main
from PySide6.QtCore import QTimer
from app.lifecycle import SingleInstanceLock

original_init = SingleInstanceLock.__init__
def isolated_lock(self, key=None, parent=None):
    original_init(self, "SpiderBuddy_test_" + uuid.uuid4().hex, parent)
SingleInstanceLock.__init__ = isolated_lock

original_startup = main.SpiderBuddyApp.startup
instances = []
def startup(self):
    instances.append(self)
    original_startup(self)
    QTimer.singleShot(50, lambda: signal.raise_signal(getattr(signal, SIGNAL_NAME)))
main.SpiderBuddyApp.startup = startup
previous = signal.getsignal(getattr(signal, SIGNAL_NAME))
assert main.main() == 0
app = instances[0]
assert app._shutting_down
assert app.instance_lock.server is None
assert not app.animation_engine._timer.isActive()
assert not app.movement_ctrl._timer.isActive()
assert not app.main_window.isVisible()
assert signal.getsignal(getattr(signal, SIGNAL_NAME)) == previous
print("CLEAN_EXIT")
'''.replace("SIGNAL_NAME", repr(signal_name))
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", APPDATA=str(tmp_path))
    result = subprocess.run([sys.executable, "-c", script], cwd=root, env=env,
                            capture_output=True, text=True, encoding="utf-8", timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "CLEAN_EXIT" in result.stdout
    assert "Traceback" not in result.stderr
