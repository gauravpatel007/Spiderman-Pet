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
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'scipy', 'pandas'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

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
    upx=True,
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
    upx=True,
    upx_exclude=[],
    name='SpiderBuddy',
)
