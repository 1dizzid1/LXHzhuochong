# -*- mode: python ; coding: utf-8 -*-

import os
import sys

PROJECT_ROOT = os.path.abspath(SPECPATH)
sys.path.insert(0, PROJECT_ROOT)

main_script = '罗小黑桌宠.py'

# 1. 数据文件
datas = [
    ('assets', 'assets'),
]

# 2. Windows 运行库（64 位）
binaries = [
    (r'C:\Windows\System32\vcruntime140.dll', '.'),
    (r'C:\Windows\System32\msvcp140.dll', '.'),
]

# 3. 隐藏导入
hiddenimports = [
    'PyQt5.QtCore',
    'PyQt5.QtGui',
    'PyQt5.QtWidgets',
    'PyQt5.sip',
    'pynput.keyboard',
    'pynput.mouse',
    'pynput.keyboard._win32',
    'pynput.mouse._win32',
]

icon_file = os.path.join(PROJECT_ROOT, 'assets', 'lxh.ico')

# 4. Analysis
a = Analysis(
    [main_script],
    pathex=[PROJECT_ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# 5. EXE：生成一个可执行 stub（单个文件）
exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name='罗小黑桌宠',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # 通常关闭UPX以避免打包时的问题
    runtime_tmpdir=None,
    console=False,
    icon=icon_file,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    onefile=True  # 添加这一行来生成单个文件
)

# 6. COLLECT：收集exe和所有依赖到同一目录（可选，因为onefile=True）
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='罗小黑桌宠'
)