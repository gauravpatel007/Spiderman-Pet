"""Single-instance ownership and newline-framed local IPC."""
import hashlib
import logging
from pathlib import Path
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
        digest = hashlib.sha256(key.encode()).hexdigest()[:24]
        self._ownership = QLockFile(str(Path(tempfile.gettempdir()) / f"spider-buddy-{digest}.lock"))
        # A long-running companion must never be treated as stale by age alone.
        self._ownership.setStaleLockTime(0)

    def _notify_primary(self):
        socket = QLocalSocket()
        socket.connectToServer(self.key)
        if not socket.waitForConnected(500):
            return False
        socket.write(b"SHOW_MAIN_WINDOW\n")
        sent = socket.bytesToWrite() == 0 or socket.waitForBytesWritten(500)
        socket.disconnectFromServer()
        return sent

    def check_and_lock(self):
        if self.is_primary:
            return True
        if not self._ownership.tryLock(1000):
            if self._notify_primary():
                self.instance_already_running.emit()
                return False
            raise RuntimeError("Spider-Buddy is already starting or its instance lock is unavailable.")
        try:
            # Support an older running version that has the IPC endpoint only.
            if self._notify_primary():
                self._ownership.unlock()
                self.instance_already_running.emit()
                return False
            self.server = QLocalServer(self)
            QLocalServer.removeServer(self.key)
            if not self.server.listen(self.key):
                raise RuntimeError(f"Cannot create companion IPC server: {self.server.errorString()}")
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
        self.is_primary = False
        self._ownership.unlock()
