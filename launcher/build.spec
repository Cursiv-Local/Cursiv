# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller build spec for Cursiv Launcher.

Usage (from repo root):
    pyinstaller launcher/build.spec

Output: dist/Cursiv/Cursiv.exe  (one-dir bundle, windowed)
macOS:  dist/Cursiv.app (built on a Mac; .github/workflows/mac-build.yml makes the .dmg)
"""

import sys
from pathlib import Path

# Qt WebEngine (Substrate Browser) was removed -- it never actually
# connected to anything real, and dropping it shrinks the bundle and
# build time noticeably (it was ~80MB of DLLs/ICU data/translations).
_extra_binaries: list = []
_extra_datas: list    = []
_extra_hidden: list   = []

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = Path(SPECPATH).parent          # repo root (one level above launcher/)
MAC = sys.platform == "darwin"
import re as _re
VERSION = _re.search(r'VERSION\s*=\s*"([^"]+)"',
                     (ROOT / "cursiv_engine" / "core" / "selfknow.py").read_text(encoding="utf-8")).group(1)
LAUNCHER = ROOT / "launcher"
CURSIV   = ROOT / "cursiv_engine"

block_cipher = None

# ── Data files bundled into the exe ──────────────────────────────────────────
datas = [
    # Icons
    (str(LAUNCHER / "resources" / "icons"), "launcher/resources/icons"),
    # cursiv_engine package (everything — models, prompts, templates)
    (str(CURSIV), "cursiv_engine"),
]
# Cursiv's own launcher code and documentation as plain text, so it can read how it
# works (core/self_source.py: "self source", "self read"). Read-only; never imported.
datas += [(str(f), "launcher") for f in sorted(LAUNCHER.glob("*.py"))]
datas += [(str(ROOT / "docs"), "docs")]
datas += [(str(ROOT / name), ".") for name in ("README.md", "TECH.md", "ARCHITECTURE.md", "CHANGELOG.md",
                                               "MODELS.md", "PRIVACY.md", "OFFLINE-DEMO.md") if (ROOT / name).exists()]


# ── Hidden imports that PyInstaller static analysis misses ───────────────────
hiddenimports = [
    # cursiv_engine sub-packages
    "cursiv_engine",
    "pypdf",                         # core/documents.py reads PDFs page by page
    "cursiv_engine.core.documents",
    "cursiv_engine.core.fieldsync",
    "cursiv_engine.core.phone_receive",
    "cursiv_engine.core.crosscheck",
    "cursiv_engine.core.demo",
    "cursiv_engine.core.profile",
    "cursiv_engine.ui",
    "cursiv_engine.ui.chat_app",
    "cursiv_engine.core",
    "cursiv_engine.core.agent",
    "cursiv_engine.core.constitution",
    "cursiv_engine.core.memory",
    "cursiv_engine.core.rate_limiter",
    "cursiv_engine.core.scan_display",
    "cursiv_engine.core.strand",
    "cursiv_engine.guardian",
    "cursiv_engine.guardian.access_gate",
    "cursiv_engine.guardian.security_questions",
    "cursiv_engine.guardian.protected",
    "cursiv_engine.guardian.identity_core",
    "bcrypt",
    "cursiv_engine.memory",
    "cursiv_engine.council",
    "cursiv_engine.obsidian",
    # launcher
    "cursiv_launcher",
    "login_dialog",
    "chat_panel",
    "crosscheck_dialog",
    "theme",
    "nav_windows",
    "field_notebook",
    "phone_receive_dialog",
    "selftest",
    "chat_commands",
    "legacy_vault_dialog",
    "postal_compose_dialog",
    "training_data_dialog",
    "portable",
    "usb_sync",                      # imported inside portable.migrate_data
    "usb_maker",
    # PyQt6
    "PyQt6",
    "PyQt6.QtWidgets",
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.sip",
    "pydantic",
    # Windows / system
    "win32api",
    "win32con",
    "win32gui",
    "win32event",
    "win32serviceutil",
    "win32service",
    "servicemanager",
    "psutil",
    "anthropic",
    "openai",
    "httpx",
    "PIL",
]

a = Analysis(
    [str(LAUNCHER / "main.py")],
    pathex=[str(ROOT), str(LAUNCHER)],
    binaries=[] + _extra_binaries,
    datas=datas + _extra_datas,
    hiddenimports=hiddenimports + _extra_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter", "matplotlib", "scipy", "IPython",
        # Heavy ML libs — not needed by launcher/chat UI; load separately at runtime
        "torch", "torchvision", "torchaudio",
        "tensorflow", "keras", "jax",
        "bitsandbytes",
        "transformers", "tokenizers", "datasets",
        "sentence_transformers",
        "sklearn", "xgboost", "lightgbm",
        "cv2", "skimage",
        # Jupyter / dev tools
        "notebook", "ipykernel", "ipywidgets",
        # Old browser/web interfaces (removed in U55)
        "gradio", "gradio_client", "streamlit", "uvicorn", "fastapi", "starlette",
        # Unused stdlib
        "unittest", "doctest", "pdb",
    ],
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
    name="Cursiv",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=not MAC,                            # UPX breaks macOS binaries
    console=False,                          # no terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # macOS: PyInstaller turns the PNG into the app's .icns (needs Pillow)
    icon=str(LAUNCHER / "resources" / "icons" / ("cursiv_256.png" if MAC else "cursiv.ico")),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=not MAC,
    upx_exclude=[],
    name="Cursiv",                          # output: dist\Cursiv\
)
if MAC:
    app = BUNDLE(
        coll,
        name="Cursiv.app",
        icon=str(LAUNCHER / "resources" / "icons" / "cursiv_256.png"),
        bundle_identifier="com.cursiv.desktop",
        version=VERSION.replace("-U", "."),          # 3.14-U71 -> 3.14.71
        info_plist={
            "CFBundleDisplayName": "Cursiv",
            "CFBundleShortVersionString": VERSION.replace("-U", "."),
            "CFBundleVersion": VERSION,
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "12.0",
            "LSApplicationCategoryType": "public.app-category.productivity",
            "NSMicrophoneUsageDescription": "Cursiv turns your voice into text on this Mac when you use Voice.",
            "NSHumanReadableCopyright": "Copyright (c) 2026 Joshua Winkler. MIT License.",
        },
    )

