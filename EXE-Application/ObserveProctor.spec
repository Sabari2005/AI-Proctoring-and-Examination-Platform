# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.utils.hooks import collect_all

datas = [('C:\\Users\\abina\\OneDrive\\Desktop\\APPLICATION\\face_landmarker.task', '.'), ('C:\\Users\\abina\\OneDrive\\Desktop\\APPLICATION\\.env', '.'), ('C:\\Users\\abina\\OneDrive\\Desktop\\APPLICATION\\assets', 'assets'), ('C:\\Users\\abina\\OneDrive\\Desktop\\APPLICATION\\.venv\\Lib\\site-packages\\mediapipe', 'mediapipe')]
binaries = [('C:\\Users\\abina\\OneDrive\\Desktop\\APPLICATION\\core\\anti_tamper.dll', 'core')]
hiddenimports = ['numpy', 'psutil', 'sounddevice', 'cryptography', 'requests', 'wmi', 'core.exam_api', 'core.proctoring_service', 'core.lockdown', 'win32api', 'win32con', 'win32gui', 'pythoncom', 'pywintypes']
hiddenimports += collect_submodules('PyQt6')
tmp_ret = collect_all('mediapipe')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('cv2')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['C:\\Users\\abina\\OneDrive\\Desktop\\APPLICATION\\main.py'],
    pathex=['C:\\Users\\abina\\OneDrive\\Desktop\\APPLICATION'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ObserveProctor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['C:\\Users\\abina\\OneDrive\\Desktop\\APPLICATION\\assets\\app_icon.ico'],
    manifest='C:\\Users\\abina\\OneDrive\\Desktop\\APPLICATION\\ObserveProctor.manifest',
)
