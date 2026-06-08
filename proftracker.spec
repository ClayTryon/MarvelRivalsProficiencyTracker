# proftracker.spec — PyInstaller build spec for ProfTracker
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files

block_cipher = None

# EasyOCR bundles model-loading code and its dependencies (torch, etc.)
easyocr_datas, easyocr_binaries, easyocr_hiddenimports = collect_all('easyocr')
torch_datas,   torch_binaries,   torch_hiddenimports   = collect_all('torch')
ic_datas,      ic_binaries,      ic_hiddenimports       = collect_all('interception')
mpl_datas = collect_data_files('matplotlib')

# RAG / Hero Wiki dependencies
llamacore_datas, llamacore_binaries, llamacore_hiddenimports = collect_all('llama_index')
st_datas, st_binaries, st_hiddenimports = collect_all('sentence_transformers')
groq_datas, groq_binaries, groq_hiddenimports = collect_all('groq')

a = Analysis(
    ['src/main.py'],
    pathex=['src'],
    binaries=(
        easyocr_binaries + torch_binaries + ic_binaries
        + llamacore_binaries + st_binaries + groq_binaries
    ),
    datas=[
        ('Icons',     'Icons'),
        ('hero_data', 'hero_data'),
        *easyocr_datas,
        *torch_datas,
        *ic_datas,
        *mpl_datas,
        *llamacore_datas,
        *st_datas,
        *groq_datas,
    ],
    hiddenimports=[
        # pywin32
        'win32api', 'win32con', 'win32gui', 'win32process',
        'win32clipboard', 'pywintypes', 'winerror',
        # interception — lazy-loaded, only used by Auto Scan
        *ic_hiddenimports,
        # PyQt6
        'PyQt6.sip',
        # EasyOCR + torch hidden imports discovered by collect_all
        *easyocr_hiddenimports,
        *torch_hiddenimports,
        # scipy is a runtime dependency of EasyOCR
        'scipy',
        'scipy.special',
        'scipy.special._cdflib',
        # matplotlib — explicit imports only (collect_all causes circular import)
        'matplotlib',
        'matplotlib._c_internal_utils',
        'matplotlib.backends.backend_qtagg',
        'matplotlib.backends.backend_agg',
        'matplotlib.figure',
        'matplotlib.axes',
        'matplotlib.pyplot',
        # openpyxl (pure Python but has lazy-loaded sub-packages)
        *collect_submodules('openpyxl'),
        # RAG / Hero Wiki
        *llamacore_hiddenimports,
        *st_hiddenimports,
        *groq_hiddenimports,
        'huggingface_hub',
        'tokenizers',
        'transformers',
        'dotenv',
        'bs4',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Strip heavy packages we definitely don't use
    excludes=['tkinter', 'IPython', 'jupyter', 'notebook'],
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
