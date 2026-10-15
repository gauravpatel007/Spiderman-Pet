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
    appdata = os.getenv("APPDATA")
    if appdata:
        log_dir = Path(appdata) / "SpiderBuddy" / "logs"
    else:
        log_dir = Path(__file__).resolve().parent.parent / "logs"

    log_dir.mkdir(parents=True, exist_ok=True)
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

    file_handler = RotatingFileHandler(str(log_file), maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    handlers.append(file_handler)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    for handler in handlers:
        handler._spider_buddy = True
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)

    logging.getLogger("SpiderBuddy").info(f"Logging initialized. Log file: {log_file}")


def bootstrap_environment() -> None:
    """Prepare environment before Qt QApplication instantiation."""
    ensure_site_packages()
    setup_logging()

    # Enable High-DPI support on Windows
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    # Preserve fractional scale factors such as 125%, 150% and 175%.
    os.environ.setdefault("QT_SCALE_FACTOR_ROUNDING_POLICY", "PassThrough")
