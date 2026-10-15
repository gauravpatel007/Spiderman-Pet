import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

import pytest
from PySide6.QtNetwork import QLocalSocket
from PySide6.QtCore import QElapsedTimer

from app.lifecycle import SingleInstanceLock
from services.settings_service import SettingsService


def pump_until(qapp, predicate):
    timer = QElapsedTimer()
    timer.start()
    while not predicate() and timer.elapsed() < 2000:
        qapp.processEvents()
    assert predicate()


def test_bootstrap_does_not_import_qt():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run([sys.executable, "-S", "-c",
        "import app.bootstrap, sys; assert 'PySide6' not in sys.modules"],
        cwd=root, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


def test_atomic_save_preserves_last_good_settings(tmp_path, monkeypatch):
    settings = SettingsService(tmp_path)
    settings.set("general.character", "tom_holland")
    before = settings.settings_file.read_bytes()
    def fail(*args):
        raise OSError("simulated interrupted replacement")
    monkeypatch.setattr(os, "replace", fail)
    settings.set("general.character", "miles_morales", auto_save=False)
    assert not settings.save()
    assert settings.settings_file.read_bytes() == before
    assert not list(tmp_path.glob("settings-*.tmp"))


def test_settings_merge_and_restart(tmp_path):
    (tmp_path / "settings.json").write_text(json.dumps({
        "general": {"character": "tom_holland", "scale": "bad"},
        "behavior": None, "system": {"start_minimized": False}}))
    settings = SettingsService(tmp_path)
    assert settings.get("general.character") == "tom_holland"
    assert settings.get("general.scale") == 1.0
    assert settings.get("behavior.enable_climbing") is True
    targets = settings.get("general.target_applications")
    targets.clear()
    assert settings.get("general.target_applications")
    settings.set("general.scale", 1.25)
    assert SettingsService(tmp_path).get("general.scale") == 1.25


def test_corrupt_settings_use_defaults_without_destroying_file(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{broken")
    assert SettingsService(tmp_path).get("general.character") == "miles_morales"
    assert path.read_text() == "{broken"


def run_client(qapp, key, partial=False):
    script = """
from app.bootstrap import ensure_site_packages
ensure_site_packages()
from PySide6.QtCore import QCoreApplication
from app.lifecycle import SingleInstanceLock
from PySide6.QtNetwork import QLocalSocket
import sys, time
app = QCoreApplication([])
key = sys.argv[1]
if sys.argv[2] == 'partial':
    socket = QLocalSocket()
    socket.connectToServer(key)
    assert socket.waitForConnected(1000)
    socket.write(b'SHOW_MAIN_')
    socket.waitForBytesWritten(500)
    time.sleep(0.1)
    socket.write(b'WINDOW\\n')
    socket.waitForBytesWritten(500)
    socket.disconnectFromServer()
else:
    lock = SingleInstanceLock(key)
    assert not lock.check_and_lock()
    assert not lock.is_primary
    lock.release()
"""
    child = subprocess.Popen([sys.executable, "-c", script, key,
        "partial" if partial else "complete"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    timer = QElapsedTimer()
    timer.start()
    try:
        while child.poll() is None and timer.elapsed() < 10000:
            qapp.processEvents()
        assert child.poll() is not None, "Secondary instance did not exit"
        stdout, stderr = child.communicate(timeout=1)
        assert child.returncode == 0, stderr.decode(errors="replace")
    finally:
        if child.poll() is None:
            child.kill()
            child.wait()


def test_second_instance_notifies_primary_and_release_allows_restart(qapp):
    key = "SpiderBuddy_test_" + uuid.uuid4().hex
    primary = SingleInstanceLock(key)
    received = []
    primary.secondary_instance_launched.connect(lambda: received.append(True))
    try:
        assert primary.check_and_lock()
        run_client(qapp, key)
        pump_until(qapp, lambda: len(received) == 1)
        run_client(qapp, key)
        pump_until(qapp, lambda: len(received) == 2)
        primary.release()
        assert primary.check_and_lock()
    finally:
        primary.release()


def test_ipc_waits_for_complete_command(qapp):
    lock = SingleInstanceLock("SpiderBuddy_test_" + uuid.uuid4().hex)
    received = []
    lock.secondary_instance_launched.connect(lambda: received.append(True))
    try:
        assert lock.check_and_lock()
        run_client(qapp, lock.key, partial=True)
        pump_until(qapp, lambda: len(received) == 1)
    finally:
        lock.release()


def test_initialization_failure_releases_lock(qapp, monkeypatch):
    import app.application as module
    key = "SpiderBuddy_test_" + uuid.uuid4().hex
    original = SingleInstanceLock.__init__
    monkeypatch.setattr(SingleInstanceLock, "__init__",
        lambda self, key_unused=None, parent=None: original(self, key, parent))
    def fail():
        raise RuntimeError("simulated initialization failure")
    monkeypatch.setattr(module, "get_settings", fail)
    with pytest.raises(RuntimeError, match="simulated"):
        module.SpiderBuddyApp(qapp)
    lock = SingleInstanceLock()
    try:
        assert lock.check_and_lock()
    finally:
        lock.release()
