# -*- mode: python ; coding: utf-8 -*-
import sys
import os

block_cipher = None

a = Analysis(
    ['app_main.py'],
    pathex=[os.path.abspath('.')],
    binaries=[],
    datas=[
        ('config.toml', '.'),
        ('redis/*', 'redis'),
        ('.venv/Scripts/*', 'Scripts'),
    ],
    hiddenimports=['rq'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='赚钱视频生成器',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,   # 关闭控制台
    windowed=True,   # 窗口模式
    icon='app_icon.ico',       # 如有图标可指定
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None )

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='赚钱视频生成器')



