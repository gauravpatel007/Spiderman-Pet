"""Inspect foreground windows using executable identities, not document titles."""
import logging
import os
import sys
import time
from dataclasses import dataclass
from typing import Optional
from PySide6.QtCore import QRect

logger = logging.getLogger('SpiderBuddy.WindowDetector')
try:
    import win32gui, win32process, win32api, psutil
    HAS_WIN32 = sys.platform == 'win32'
except ImportError:
    HAS_WIN32 = False


@dataclass
class WindowInfo:
    hwnd: int
    title: str
    process_name: str
    pid: int
    rect: QRect  # Native physical screen pixels; convert at the overlay boundary.
    is_minimized: bool
    is_visible: bool
    executable_path: str = ''
    application_name: str = ''
    is_maximized: bool = False

    @property
    def identity(self):
        return {'executable_path': self.executable_path,
                'process_name': self.process_name,
                'display_name': self.application_name or self.process_name}


class WindowDetector:
    _process_cache = {}
    _name_cache = {}

    @classmethod
    def _process_identity(cls, pid):
        now = time.monotonic()
        cached = cls._process_cache.get(pid)
        if cached and now - cached[0] < 2:
            return cached[1:]
        name, path, display = '', '', ''
        try:
            proc = psutil.Process(pid)
            name = proc.name()
            try:
                path = proc.exe()
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                pass
            display = cls._name_cache.get(path, '')
            if path and not display:
                try:
                    translations = win32api.GetFileVersionInfo(path, r'\VarFileInfo\Translation')
                    lang, code = translations[0]
                    display = win32api.GetFileVersionInfo(path,
                        f'\\StringFileInfo\\{lang:04x}{code:04x}\\ProductName')
                except Exception:
                    display = name.removesuffix('.exe')
                cls._name_cache[path] = display
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass
        if len(cls._process_cache) > 256:
            cls._process_cache.clear()
        cls._process_cache[pid] = (now, name, path, display)
        return name, path, display

    @classmethod
    def inspect(cls, hwnd) -> Optional[WindowInfo]:
        if not HAS_WIN32 or not hwnd:
            return None
        try:
            if not win32gui.IsWindow(hwnd):
                return None
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            name, path, display = cls._process_identity(pid)
            l,t,r,b = win32gui.GetWindowRect(hwnd)
            visible = bool(win32gui.IsWindowVisible(hwnd))
            # Cloaked windows (e.g. another virtual desktop) must not host a pet.
            import ctypes
            from ctypes import wintypes
            frame = wintypes.RECT()
            result = ctypes.windll.dwmapi.DwmGetWindowAttribute(ctypes.c_void_p(hwnd), 9,
                ctypes.byref(frame), ctypes.sizeof(frame))
            if result == 0 and frame.right > frame.left and frame.bottom > frame.top:
                l,t,r,b = frame.left,frame.top,frame.right,frame.bottom
            cloaked = ctypes.c_uint(0)
            ctypes.windll.dwmapi.DwmGetWindowAttribute(ctypes.c_void_p(hwnd), 14,
                ctypes.byref(cloaked), ctypes.sizeof(cloaked))
            return WindowInfo(hwnd, win32gui.GetWindowText(hwnd).strip(), name, pid,
                QRect(l,t,max(0,r-l),max(0,b-t)), bool(win32gui.IsIconic(hwnd)),
                visible and not cloaked.value, path, display,
                bool(win32gui.GetWindowPlacement(hwnd)[1] == 3))
        except Exception as exc:
            logger.debug('Window disappeared or cannot be inspected: %s', exc)
            return None

    @classmethod
    def get_visible_windows(cls):
        windows=[]
        if HAS_WIN32:
            def collect(hwnd, _):
                win=cls.inspect(hwnd)
                if win and win.is_visible and win.title and win.pid != os.getpid():
                    windows.append(win)
                return True
            try:
                win32gui.EnumWindows(collect,None)
            except Exception as exc:
                logger.debug('Window enumeration failed: %s',exc)
        return windows

    @classmethod
    def get_foreground_window(cls):
        return cls.inspect(win32gui.GetForegroundWindow()) if HAS_WIN32 else None

    @classmethod
    def get_installed_applications(cls):
        """Read Windows App Paths registrations without launching executables."""
        if not HAS_WIN32:
            return []
        import winreg
        records = {}
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
                try:
                    with winreg.OpenKey(hive, r'Software\Microsoft\Windows\CurrentVersion\App Paths',
                                        0, winreg.KEY_READ | view) as registry:
                        for index in range(winreg.QueryInfoKey(registry)[0]):
                            name = winreg.EnumKey(registry, index)
                            try:
                                with winreg.OpenKey(registry, name) as entry:
                                    path = os.path.expandvars(winreg.QueryValue(entry, None)).strip('"')
                                if os.path.isfile(path):
                                    records[os.path.normcase(path)] = {
                                        'executable_path': path,
                                        'process_name': os.path.basename(path),
                                        'display_name': os.path.splitext(os.path.basename(path))[0]}
                            except OSError:
                                continue
                except OSError:
                    continue
        return list(records.values())

    @staticmethod
    def matches(window, selection):
        if isinstance(selection,dict):
            path=selection.get('executable_path','')
            if path:
                return bool(window.executable_path) and os.path.normcase(path)==os.path.normcase(window.executable_path)
            return bool(selection.get('process_name')) and selection['process_name'].casefold()==window.process_name.casefold()
        # Old preferences/custom entries match exact executable/product names.
        # A browser document title can never impersonate a selected application.
        value=str(selection).strip().casefold()
        return bool(value) and value in {window.process_name.casefold(),
            window.process_name.removesuffix('.exe').casefold(),
            window.application_name.casefold(),window.executable_path.casefold()}

    @classmethod
    def find_window_by_title_substring(cls, selection):
        # Compatibility entry point; deliberately no longer matches title substrings.
        return next((w for w in cls.get_visible_windows() if cls.matches(w,selection)),None)
