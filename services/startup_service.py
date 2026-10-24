"""Windows Startup / Autorun Management Service."""
import logging
import os
import sys

logger = logging.getLogger("SpiderBuddy.StartupService")

try:
    import winreg
    HAS_WINREG = True
except ImportError:
    HAS_WINREG = False


class StartupService:
    """Manages Windows startup registry entry for Spider-Buddy."""

    REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
    APP_NAME = "SpiderBuddy"

    @classmethod
    def get_executable_command(cls) -> str:
        """Return the executable or python command to launch Spider-Buddy without a console window."""
        if getattr(sys, "frozen", False):
            # Built with PyInstaller
            return f'"{sys.executable}"'
        else:
            # Running as Python script: prefer pythonw.exe to prevent terminal/console window
            exec_dir = os.path.dirname(sys.executable)
            pythonw = os.path.join(exec_dir, "pythonw.exe")
            if not os.path.isfile(pythonw):
                if os.path.isfile(r"C:\Program Files\Python313\pythonw.exe"):
                    pythonw = r"C:\Program Files\Python313\pythonw.exe"
                else:
                    pythonw = sys.executable
            main_script = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main.py"))
            return f'"{pythonw}" "{main_script}"'

    @classmethod
    def is_startup_enabled(cls) -> bool:
        """Check if Spider-Buddy is registered to run on Windows startup."""
        if not HAS_WINREG:
            return False
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.REG_KEY, 0, winreg.KEY_READ) as key:
                value, _ = winreg.QueryValueEx(key, cls.APP_NAME)
                return bool(value)
        except (FileNotFoundError, OSError):
            return False

    @classmethod
    def set_startup_enabled(cls, enable: bool) -> bool:
        """Enable or disable autorun on Windows startup."""
        if not HAS_WINREG:
            logger.warning("Windows registry (winreg) not available on this platform.")
            return False

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.REG_KEY, 0, winreg.KEY_SET_VALUE) as key:
                if enable:
                    cmd = cls.get_executable_command()
                    winreg.SetValueEx(key, cls.APP_NAME, 0, winreg.REG_SZ, cmd)
                    logger.info(f"Registered Spider-Buddy startup command: {cmd}")
                else:
                    try:
                        winreg.DeleteValue(key, cls.APP_NAME)
                        logger.info("Removed Spider-Buddy from Windows startup.")
                    except FileNotFoundError:
                        pass
            return True
        except Exception as e:
            logger.error(f"Failed to update Windows startup registry: {e}")
            return False
