# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('settings.py', '.'), ('file_manager.py', '.'), ('screenshot.py', '.'), ('exporter.py', '.'), ('comment_popup.py', '.'), ('stitch_tool.py', '.'), ('compare_tool.py', '.'), ('toast.py', '.'), ('ui.py', '.'), ('Docilio.ico', '.')],
    hiddenimports=['PIL', 'PIL._imagingtk', 'mss', 'keyboard', 'openpyxl', 'docx', 'reportlab', 'pptx'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['numpy', 'scipy', 'matplotlib', 'pandas', 'IPython', 'jupyter', 'notebook', 'pytest', 'unittest', 'tkinter.test'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Docilio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['Docilio.ico'],
    manifest='manifest.xml',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Docilio',
)
