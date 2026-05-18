# proftracker.spec — PyInstaller build spec for ProfTracker
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files

block_cipher = None

# EasyOCR bundles model-loading code and its dependencies (torch, etc.)
easyocr_datas, easyocr_binaries, easyocr_hiddenimports = collect_all('easyocr')
torch_datas,   torch_binaries,   torch_hiddenimports   = collect_all('torch')
mpl_datas,     mpl_binaries,     mpl_hiddenimports     = collect_all('matplotlib')

a = Analysis(
    ['src/main.py'],
    pathex=['src'],
    binaries=easyocr_binaries + torch_binaries + mpl_binaries,
    datas=[
        ('Icons', 'Icons'),
        ('Icons/app_icon.ico', 'Icons'),
        *easyocr_datas,
        *torch_datas,
        *mpl_datas,
    ],
    hiddenimports=[
        # pywin32
        'win32api', 'win32con', 'win32gui', 'win32process',
        'win32clipboard', 'pywintypes', 'winerror',
        # PyQt6
        'PyQt6.sip',
        # EasyOCR + torch hidden imports discovered by collect_all
        *easyocr_hiddenimports,
        *torch_hiddenimports,
        # scipy is a runtime dependency of EasyOCR
        'scipy',
        'scipy.special',
        'scipy.special._cdflib',
        # matplotlib QtAgg backend
        'matplotlib.backends.backend_qtagg',
        'matplotlib.backends.backend_agg',
        *mpl_hiddenimports,
        # openpyxl (pure Python but has lazy-loaded sub-packages)
        *collect_submodules('openpyxl'),
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Strip heavy packages we definitely don't use
    excludes=['tkinter', 'matplotlib', 'IPython', 'jupyter', 'notebook'],
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
    name='ProfTracker',
    icon='Icons/app_icon.ico',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # UPX can break torch DLLs; leave off
    console=False,      # no terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='ProfTracker',
)
