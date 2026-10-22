"""Explicit USB operation services provided by usb_maker.

Paths, model choices, copy callbacks and existing filesystem helpers remain
reviewable here; the operation module receives these services explicitly.
"""
from typing import Any, Protocol


class UsbRuntime(Protocol):
    FAT32_MAX: Any
    GB: Any
    MTIME_SLACK: Any
    OLLAMA_API: Any
    PRIVATE_MARKER: Any
    PRUNED_DIRS: Any
    Path: Any
    README: Any
    REQUIRED_CHAT: Any
    REQUIRED_EMBED: Any
    START_BAT: Any
    _BUNDLED_LICENSES: Any
    _EXTRA_TERMS: Any
    _LICENSE_LAYER: Any
    __file__: Any
    _download_ollama: Any
    _is_personal: Any
    _needs_copy: Any
    _program_files: Any
    _safe_name: Any
    _volume_info: Any
    build_plan: Any
    copy_files: Any
    ctypes: Any
    json: Any
    list_models: Any
    model_license: Any
    models_dir: Any
    ollama_dir: Any
    os: Any
    program_dir: Any
    pull_model: Any
    required_names: Any
    shutil: Any
    stale_files: Any
    string: Any
    sys: Any
    tempfile: Any
    tidy_root: Any
    update_plan: Any
    urllib: Any
    verify_usb: Any
    write_licenses: Any
    zipfile: Any
