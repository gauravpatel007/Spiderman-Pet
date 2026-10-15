"""One foreground poller shared by application containment and ownership UI."""
from PySide6.QtCore import QObject,QTimer,Signal
from .window_detector import WindowDetector


class WindowTracker(QObject):
    foreground_changed=Signal(object)

    def __init__(self,poll_interval_ms=100,parent=None):
        super().__init__(parent)
        self._snapshot=None
        self._timer=QTimer(self)
        self._timer.setInterval(poll_interval_ms)
        self._timer.timeout.connect(self.refresh)

    def start(self):
        self._snapshot=None
        self.refresh()
        self._timer.start()

    def stop(self):
        self._timer.stop()

    def refresh(self, force=False):
        window=WindowDetector.get_foreground_window()
        snapshot=(window.hwnd,window.pid,window.rect.getRect(),window.is_visible,
                  window.is_minimized,window.executable_path,window.process_name) if window else None
        if force or snapshot!=self._snapshot:
            self._snapshot=snapshot
            self.foreground_changed.emit(window)

    def set_target_applications(self, selections):
        self.refresh(force=True)
