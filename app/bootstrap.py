"""Environment bootstrapping, logging, and DPI configuration."""
import logging
from logging.handlers import RotatingFileHandler
import os
import site
import sys
from pathlib import Path


def ensure_site_packages() -> None:
    """Ensure user roaming and local site-packages are added to sys.path."""
    user_site = site.getusersitepackages()
    if os.path.exists(user_site) and user_site not in sys.path:
        sys.path.insert(0, user_site)

    version = f"Python{sys.version_info.major}{sys.version_info.minor}"
    roaming_site = str(Path.home() / "AppData" / "Roaming" / "Python" / version / "site-packages")
    if os.path.exists(roaming_site) and roaming_site not in sys.path:
        sys.path.insert(0, roaming_site)


def setup_logging() -> None:
    """Configure structured logging to console and persistent log file."""
    root_logger = logging.getLogger()
    if any(getattr(handler, "_spider_buddy", False) for handler in root_logger.handlers):
        return
    log_dir = None
    appdata = os.getenv("APPDATA")
    candidates = []
    if appdata:
        candidates.append(Path(appdata) / "SpiderBuddy" / "logs")
    candidates.append(Path.home() / ".spiderbuddy" / "logs")
    candidates.append(Path(__file__).resolve().parent.parent / "logs")
    import tempfile
    candidates.append(Path(tempfile.gettempdir()) / "SpiderBuddy" / "logs")

    for cand in candidates:
        try:
            cand.mkdir(parents=True, exist_ok=True)
            log_dir = cand
            break
        except (PermissionError, FileExistsError, OSError):
            if cand.exists() and cand.is_dir():
                log_dir = cand
                break
            continue

    if log_dir is None:
        log_dir = Path(tempfile.gettempdir())

    log_file = log_dir / "spider_buddy.log"

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Ensure stdout handles emojis on Windows console
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    handlers = []
    if sys.stdout is not None:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        handlers.append(console_handler)

    file_handler = None
    log_candidates = [
        log_dir / "spider_buddy.log",
        Path.home() / ".spiderbuddy" / "spider_buddy.log",
        Path(tempfile.gettempdir()) / "spider_buddy.log"
    ]

    for cand_file in log_candidates:
        try:
            cand_file.parent.mkdir(parents=True, exist_ok=True)
            handler = RotatingFileHandler(str(cand_file), maxBytes=2_000_000, backupCount=3, encoding="utf-8")
            handler.setLevel(logging.DEBUG)
            handlers.append(handler)
            file_handler = handler
            log_file = cand_file
            break
        except Exception:
            continue

    if file_handler is None and sys.stdout is not None:
        sys.stdout.write("Notice: Could not attach file logger to any candidate location; using console logger.\n")

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    for handler in handlers:
        handler._spider_buddy = True
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)

    logging.getLogger("SpiderBuddy").info(f"Logging initialized. Log file: {log_file}")


def ensure_interactive_desktop() -> None:
    """Ensure process and GUI threads are attached to the interactive user desktop on Windows."""
    if sys.platform != "win32":
        return
    try:
        import win32service, win32con
        desk = win32service.OpenDesktop("Default", 0, False, win32con.GENERIC_ALL)
        if desk:
            desk.SetThreadDesktop()
    except Exception:
        pass


def get_user_data_dir() -> Path:
    """Return persistent user application data directory."""
    appdata = os.getenv("APPDATA")
    if appdata:
        d = Path(appdata) / "SpiderBuddy"
    else:
        d = Path.home() / ".spider-buddy"
    d.mkdir(parents=True, exist_ok=True)
    return d


def bootstrap_environment() -> None:
    """Prepare environment before Qt QApplication instantiation."""
    ensure_interactive_desktop()
    ensure_site_packages()
    setup_logging()

    # Enable High-DPI support on Windows
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    # Preserve fractional scale factors such as 125%, 150% and 175%.
    os.environ.setdefault("QT_SCALE_FACTOR_ROUNDING_POLICY", "PassThrough")

    # Configure Chromium for seamless DWM DirectComposition presentation without cursor or frame flicker
    existing_flags = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "")
    flags_to_add = (
        "--use-angle=d3d11 "
        "--disable-features=CalculateNativeWinOcclusion,WindowOcclusionCalculation,MrcMultiplaneOverlay "
        "--disable-backgrounding-occluded-windows"
    )
    if "--use-angle=d3d11" not in existing_flags:
        os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = f"{existing_flags} {flags_to_add}".strip()
