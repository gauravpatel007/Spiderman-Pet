"""Application lifecycle, bootstrapping, and orchestration package."""
from .bootstrap import bootstrap_environment

__all__ = ["SingleInstanceLock", "bootstrap_environment", "SpiderBuddyApp"]


def __getattr__(name):
    # Importing app.bootstrap must not load Qt before dependency setup.
    if name == "SingleInstanceLock":
        from .lifecycle import SingleInstanceLock
        return SingleInstanceLock
    if name == "SpiderBuddyApp":
        from .application import SpiderBuddyApp
        return SpiderBuddyApp
    raise AttributeError(name)
