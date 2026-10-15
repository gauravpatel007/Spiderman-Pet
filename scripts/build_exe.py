"""Automated build script for packaging Spider-Buddy into a standalone Windows executable."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Ensure UTF-8 console output on Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def build():
    root = Path(__file__).resolve().parent.parent
    spec_file = root / "SpiderBuddy.spec"
    dist_dir = root / "dist" / "SpiderBuddy"

    print("==================================================")
    print("[*] Spider-Buddy Windows Executable Packaging")
    print("==================================================")

    # 1. Ensure icons exist
    icons_dir = root / "assets" / "icons"
    if not (icons_dir / "spider.ico").exists() or not (icons_dir / "tray.png").exists():
        print("[+] Generating application icons...")
        subprocess.run([sys.executable, str(root / "scripts" / "generate_app_icons.py")], check=True)

    # 2. Run PyInstaller
    print(f"[+] Building executable from {spec_file.name}...")
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", str(spec_file)]
    res = subprocess.run(cmd, cwd=str(root))
    if res.returncode != 0:
        print(f"[-] Packaging failed with return code {res.returncode}")
        return res.returncode

    # 3. Ensure assets exist directly alongside the executable for easy user access & customization
    print("[+] Mirroring asset directories next to executable...")
    for folder in ["characters", "config", "assets"]:
        src = root / folder
        dest = dist_dir / folder
        if src.exists() and not dest.exists():
            shutil.copytree(src, dest)

    # 4. Verify output
    exe_path = dist_dir / "SpiderBuddy.exe"
    if exe_path.exists():
        print("==================================================")
        print("[+] SUCCESS: Spider-Buddy packaged successfully!")
        print(f"[*] Output directory: {dist_dir}")
        print(f"[*] Executable: {exe_path}")
        print("==================================================")
        return 0
    else:
        print(f"[-] Error: Executable was not found at {exe_path}")
        return 1

if __name__ == "__main__":
    sys.exit(build())
