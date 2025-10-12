# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for Parakeet TDT Transcriber.

Usage:
    PARAKEET_FFMPEG_PATH=/absolute/path/to/ffmpeg \
    uv run pyinstaller packaging/pyinstaller/parakeet.spec

The spec bundles PySide6, MLX, parakeet-mlx assets, the sounddevice
backend, and an optional ffmpeg binary. See README for detailed steps.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
)

# ----------------------------------------------------------------------------
# Paths and resource configuration
# ----------------------------------------------------------------------------
_spec_path = Path(globals().get("__file__", sys.argv[0])).resolve()
PROJECT_ROOT = _spec_path.parents[2]
PACKAGE_ROOT = PROJECT_ROOT / "app"

# Version helpers -------------------------------------------------------------


def _normalize_version(raw: str | None) -> str:
    if not raw:
        return "0.0.0"
    return raw.removeprefix("v")


APP_VERSION = _normalize_version(
    os.environ.get("PARAKEET_VERSION") or os.environ.get("GITHUB_REF_NAME")
)

# Optional ffmpeg bundling ----------------------------------------------------
FFMPEG_ENV_VAR = "PARAKEET_FFMPEG_PATH"
ffmpeg_path = os.environ.get(FFMPEG_ENV_VAR)
ffmpeg_datas = []
if ffmpeg_path:
    candidate = Path(ffmpeg_path).expanduser().resolve()
    if candidate.exists() and candidate.is_file():
        ffmpeg_datas.append((str(candidate), "bin"))
    else:
        raise FileNotFoundError(
            f"環境変数 {FFMPEG_ENV_VAR} で指定されたパスが存在しません: {candidate}"
        )

# Qt, parakeet, MLX assets ----------------------------------------------------
datas = []
datas += collect_data_files("parakeet_mlx")
datas += collect_data_files("mlx")
datas += [
    (str(PROJECT_ROOT / "README.md"), "."),
    (str(PROJECT_ROOT / "LICENSE"), "."),
]
datas += ffmpeg_datas

# Dynamic libraries required by MLX ------------------------------------------
binaries = []
binaries += collect_dynamic_libs("mlx")

# Hidden imports --------------------------------------------------------------
hiddenimports = []
hiddenimports += collect_submodules("parakeet_mlx")
hiddenimports += collect_submodules("mlx")

block_cipher = None

# ----------------------------------------------------------------------------
# Standard PyInstaller spec configuration
# ----------------------------------------------------------------------------
a = Analysis(
    [str(PROJECT_ROOT / "main.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    name="parakeet-tdt",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=None,
)

bundle = BUNDLE(
    exe,
    name="Parakeet TDT.app",
    icon=str(PROJECT_ROOT / "assets" / "icon.icns"),
    bundle_identifier="com.parakeet.tdt",
    info_plist={
        "CFBundleDisplayName": "Parakeet TDT",
        "CFBundleName": "Parakeet TDT",
        "CFBundleExecutable": "parakeet-tdt",
        "CFBundleVersion": APP_VERSION,
        "CFBundleShortVersionString": APP_VERSION,
        "LSMinimumSystemVersion": "14.0",
        "NSMicrophoneUsageDescription": "音声を書き起こすためにマイクを利用します。",
    },
)

coll = COLLECT(
    bundle,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="parakeet-tdt",
)
