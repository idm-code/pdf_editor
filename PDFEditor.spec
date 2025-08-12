# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

datas = []
fonts_dir = os.path.join('app', 'fonts')
if os.path.isdir(fonts_dir):
    datas.append((fonts_dir, os.path.join('app', 'fonts')))

icon_file = os.path.join('app', 'assets', 'favicon.ico')
if not os.path.isfile(icon_file):
    icon_file = None

hiddenimports = collect_submodules('pikepdf')

a = Analysis(
    ['app/main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='PDFEditor',
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon=icon_file
)