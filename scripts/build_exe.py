"""Automated build script for packaging Spider-Buddy into a standalone Windows executable."""
import os
import shutil
import subprocess
import sys
import zipfile
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

    # 3. Mirror asset directories next to executable
    print("[+] Mirroring asset directories next to executable...")
    for folder in ["characters", "config", "assets", "Frontend"]:
        src = root / folder
        dest = dist_dir / folder
        if src.exists():
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True)
            shutil.copytree(src, dest)

    # 4. Post-build sanitization and verification:
    internal_dir = dist_dir / "_internal"
    pyside_dir = internal_dir / "PySide6"

    # Remove any conflicting ICU libraries if they leaked in
    for bad_file in ["icuuc.dll", "icudt78.dll", "icuin.dll"]:
        for loc in [internal_dir / bad_file, pyside_dir / bad_file]:
            if loc.exists():
                print(f"[!] Removing conflicting ICU library: {loc.name}")
                loc.unlink()

    # Ensure shiboken6.abi3.dll exists in both PySide6 and internal
    try:
        import shiboken6
        shiboken_src = Path(shiboken6.__file__).parent / "shiboken6.abi3.dll"
        if shiboken_src.exists():
            for target_dir in [internal_dir, pyside_dir]:
                target = target_dir / "shiboken6.abi3.dll"
                if not target.exists():
                    print(f"[+] Placing shiboken6.abi3.dll in {target_dir.name}")
                    shutil.copy2(shiboken_src, target)
    except Exception as e:
        print(f"[-] Shiboken verification warning: {e}")

    # 5. Verify output
    exe_path = dist_dir / "SpiderBuddy.exe"
    if exe_path.exists():
        print("==================================================")
        print("[+] SUCCESS: Spider-Buddy packaged successfully!")
        print(f"[*] Output directory: {dist_dir}")
        print(f"[*] Executable: {exe_path}")
        print("==================================================")

        # 6. Create distributable ZIP archive
        zip_path = root / "dist" / "SpiderBuddy-v1.0.0.zip"
        print(f"[+] Creating distributable archive: {zip_path.name}...")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root_path, dirs, files in os.walk(dist_dir):
                for f in files:
                    file_full_path = Path(root_path) / f
                    arcname = os.path.join("SpiderBuddy", os.path.relpath(file_full_path, dist_dir))
                    zf.write(file_full_path, arcname)

        print(f"[+] Package ready: {zip_path} ({zip_path.stat().st_size / (1024*1024):.1f} MB)")
        return 0
    else:
        print(f"[-] Error: Executable was not found at {exe_path}")
        return 1

if __name__ == "__main__":
    sys.exit(build())
