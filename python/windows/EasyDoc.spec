# PyInstaller spec for EasyDoc on Windows 10/11.
#   pyinstaller windows/EasyDoc.spec
# Produces dist/EasyDoc/EasyDoc.exe (onedir) — run build_windows.bat instead.
# -*- mode: python ; coding: utf-8 -*-
block_cipher = None
a = Analysis(
    ['..\\src\\easydoc\\gui.py'],
    pathex=['..\\src'],
    binaries=[],
    datas=[('..\\src\\easydoc', 'easydoc')],
    hiddenimports=['fitz', 'pymupdf', 'docx', 'pptx', 'openpyxl', 'PIL', 'pypdf'],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name='EasyDoc', debug=False, bootloader_ignore_signals=False,
    strip=False, upx=True, console=False,
)
coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, strip=False, upx=True,
               upx_exclude=[], name='EasyDoc')
