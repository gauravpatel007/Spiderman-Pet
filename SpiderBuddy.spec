# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from pathlib import Path

block_cipher = None

project_dir = os.path.abspath(SPECPATH)

datas = [
    (os.path.join(project_dir, 'characters'), 'characters'),
    (os.path.join(project_dir, 'config'), 'config'),
    (os.path.join(project_dir, 'assets'), 'assets'),
    (os.path.join(project_dir, 'ui', 'qml'), 'ui/qml'),
    (os.path.join(project_dir, 'Frontend'), 'Frontend'),
]

# Explicitly collect Shiboken6 runtime DLLs into PySide6, shiboken6, and root _internal
shiboken_binaries = []
try:
    import shiboken6
    shiboken_dir = os.path.dirname(shiboken6.__file__)
    for f in os.listdir(shiboken_dir):
        if f.lower().endswith(('.dll', '.pyd')):
            src = os.path.join(shiboken_dir, f)
            shiboken_binaries.append((src, 'shiboken6'))
            shiboken_binaries.append((src, 'PySide6'))
            shiboken_binaries.append((src, '.'))
except Exception as e:
    print(f"Warning: Could not collect shiboken6 binaries: {e}")

hidden_imports = [
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.QtNetwork',
    'PySide6.QtQml',
    'PySide6.QtQuick',
    'PySide6.QtQuickWidgets',
    'PySide6.QtWebEngineWidgets',
    'PySide6.QtWebEngineCore',
    'shiboken6',
    'http.server',
    'socketserver',
    'win32gui',
    'win32process',
    'win32con',
    'win32api',
    'win32ts',
    'psutil',
    'PIL',
    'PIL.Image',
    'app',
    'core',
    'overlay',
    'services',
    'ui',
]

a = Analysis(
    ['main.py'],
    pathex=[project_dir],
    binaries=shiboken_binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5', 'PyQt6', 'PyQt5_sip', 'PyQt6_sip', 'torch', 'tensorflow', 'tensorboard', 'scipy', 'matplotlib', 'numpy.testing', 'pandas', 'tkinter', 'IPython', 'jupyter'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Strip conflicting ICU dlls (Qt6 on Windows relies on C:\Windows\System32\icuuc.dll)
a.binaries = [x for x in a.binaries if not os.path.basename(x[0]).lower().startswith(('icuuc', 'icudt', 'icuin'))]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SpiderBuddy',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(project_dir, 'assets', 'icons', 'spider.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='SpiderBuddy',
)
