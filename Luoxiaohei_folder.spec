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
    hookspath=[],  # 尝试添加钩子路径
    hooksconfig={},  # 尝试添加钩子配置
    runtime_hooks=[],  # 尝试添加运行时钩子
    excludes=[],  # 尝试排除不需要的文件
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# 5. EXE：生成一个可执行 stub（放到文件夹里）
exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,   # 关键：不要把所有二进制塞进 exe
    name='罗小黑桌宠',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,               # 文件夹模式通常关 UPX，避免冗余
    console=False,
    icon=icon_file,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# 6. COLLECT：把 exe + 所有依赖收集到同一目录（文件夹形式）
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='罗小黑桌宠_folder'
)