# -*- mode: python ; coding: utf-8 -*-
# MxdTool 打包规格（单文件、无控制台）
# 构建：build.bat  或  pyinstaller --clean --noconfirm MxdTool.spec

a = Analysis(
    ['mxd_gui.py'],
    pathex=['.'],
    binaries=[],
    datas=[('assets/app.ico', 'assets')],
    hiddenimports=['mxdlib', 'Crypto'],
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
    name='MxdTool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/app.ico',
)
