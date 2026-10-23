"""Inspect an export tree without following filesystem substitutions."""
import os
from pathlib import Path, PurePosixPath
import stat


def inventory(folder):
    folder = Path(folder)
    if folder.is_symlink() or (hasattr(folder, 'is_junction') and folder.is_junction()):
        raise ValueError('Export root is a symbolic link or junction')
    root = folder.resolve(strict=True)
    if not root.is_dir():
        raise ValueError('Export root must be a directory')
    files = {}
    for current, dirs, names in os.walk(root, followlinks=False):
        for name in dirs + names:
            path = Path(current) / name
            mode = path.lstat()
            if (path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction()) or
                    not (stat.S_ISREG(mode.st_mode) or stat.S_ISDIR(mode.st_mode))):
                raise ValueError('Unsupported link or filesystem object in export: ' + name)
            if not path.resolve(strict=True).is_relative_to(root):
                raise ValueError('Export entry is outside the export root')
            if stat.S_ISREG(mode.st_mode):
                if mode.st_nlink > 1:
                    raise ValueError('Hard-linked export files are unsupported')
                files[path.relative_to(root).as_posix()] = path
    return files


def valid_name(name):
    return (isinstance(name, str) and bool(name) and not PurePosixPath(name).is_absolute()
            and '..' not in PurePosixPath(name).parts and '\\' not in name and ':' not in name)
