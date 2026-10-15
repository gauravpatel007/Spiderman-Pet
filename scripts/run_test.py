import sys
from pathlib import Path

# Add project root and site-packages
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app.bootstrap import ensure_site_packages
ensure_site_packages()

import pytest

if __name__ == "__main__":
    test_files = [
        "tests/test_interactive_features.py",
        "tests/test_core.py",
    ]
    sys.exit(pytest.main(test_files + ["-v"]))
