"""Single-instance ownership and newline-framed local IPC."""
import hashlib
import logging
from pathlib import Path
import sys
import tempfile
from typing import Optional

from PySide6.QtCore import QObject, Signal, QLockFile
from PySide6.QtNetwork import QLocalServer, QLocalSocket

logger = logging.getLogger("SpiderBuddy.Lifecycle")


class SingleInstanceLock(QObject):
    instance_already_running = Signal()
    secondary_instance_launched = Signal()

    def __init__(self, key="SpiderBuddy_Singleton_Lock_Key", parent: Optional[QObject] = None):
        super().__init__(parent)
        self.key = key
        self.server = None
        self.is_primary = False
        self._mutex_handle = None
        digest = hashlib.sha256(key.encode()).hexdigest()[:24]
        self._ownership = QLockFile(str(Path(tempfile.gettempdir()) / f"spider-buddy-{digest}.lock"))
        self._ownership.setStaleLockTime(0)

    def _notify_primary(self):
        socket = QLocalSocket()
        socket.connectToServer(self.key)
        if not socket.waitForConnected(700):
            return False
        socket.write(b"SHOW_MAIN_WINDOW\n")
        sent = socket.bytesToWrite() == 0 or socket.waitForBytesWritten(500)
        socket.disconnectFromServer()
        return sent

    def check_and_lock(self):
        if self.is_primary:
            return True

        # 1. On Windows, check native Win32 Named Mutex first (immune to stale temp files)
        if sys.platform == "win32":
            try:
                import ctypes
                mutex_name = f"Local\\{self.key}_Mutex"
                self._mutex_handle = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
                last_err = ctypes.windll.kernel32.GetLastError()
                if last_err == 183:  # ERROR_ALREADY_EXISTS
                    logger.info("Existing Spider-Buddy instance detected via Win32 Named Mutex.")
                    self._notify_primary()
                    self.instance_already_running.emit()
                    return False
            except Exception as e:
                logger.debug(f"Win32 mutex check note: {e}")

        # 2. Check QLockFile
        if not self._ownership.tryLock(1000):
            logger.info("Existing Spider-Buddy instance detected via lock file.")
            self._notify_primary()
            self.instance_already_running.emit()
            return False

        try:
            # Support an older running version that has the IPC endpoint only.
            if self._notify_primary():
                self._ownership.unlock()
                self.instance_already_running.emit()
                return False
            self.server = QLocalServer(self)
            QLocalServer.removeServer(self.key)
            if not self.server.listen(self.key):
                logger.warning(f"Cannot create companion IPC server: {self.server.errorString()}")
            else:
                self.server.newConnection.connect(self._on_new_connection)
            self.is_primary = True
            logger.info("Primary Spider-Buddy instance acquired.")
            return True
        except Exception:
            self.release()
            raise

    def _on_new_connection(self):
        while self.server and self.server.hasPendingConnections():
            client = self.server.nextPendingConnection()
            client.readyRead.connect(lambda client=client: self._handle_client_message(client))
            client.disconnected.connect(client.deleteLater)
            # Data may have arrived before readyRead was connected.
            self._handle_client_message(client)

    def _handle_client_message(self, socket):
        if socket.bytesAvailable() > 1024:
            socket.abort()
            return
        while socket.canReadLine():
            if bytes(socket.readLine()).strip() == b"SHOW_MAIN_WINDOW":
                self.secondary_instance_launched.emit()
            socket.disconnectFromServer()

    def release(self):
        if self.server:
            self.server.close()
            self.server.deleteLater()
            self.server = None
        if self._mutex_handle:
            try:
                import ctypes
                ctypes.windll.kernel32.CloseHandle(self._mutex_handle)
                self._mutex_handle = None
            except Exception:
                pass
        self.is_primary = False
        self._ownership.unlock()
