"""Inventario de solo lectura para el piloto local de MODAX.

No implementa copia, movimiento ni eliminacion.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
import os
import re
import stat


@dataclass(frozen=True)
class FileRecord:
    relative_path: str
    name: str
    extension: str
    size_bytes: int
    modified_at: datetime
    created_at: datetime
    is_old: bool
    protected: bool


@dataclass
class Inventory:
    root: str
    cutoff: date
    files: list[FileRecord] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    excluded_dirs: list[str] = field(default_factory=list)
    excluded_files: int = 0

    @property
    def total_bytes(self) -> int:
        return sum(item.size_bytes for item in self.files)

    @property
    def old_count(self) -> int:
        return sum(item.is_old for item in self.files)


def validate_local_root(raw: str) -> Path:
    """Accept only existing, non-link local directories on Windows.

    A network drive mapped to a letter is also rejected using GetDriveTypeW.
    On non-Windows platforms this function refuses execution: Windows-only pilot.
    """
    if os.name != "nt":
        raise ValueError("Este piloto solo puede ejecutarse en Windows.")
    if not raw or raw.startswith(("\\\\", "//")):
        raise ValueError("No se permiten rutas de red UNC.")
    path = Path(raw).absolute()
    if not path.exists() or not path.is_dir() or path.is_symlink():
        raise ValueError("Selecciona una carpeta local existente.")
    import ctypes
    from ctypes import wintypes
    drive = path.drive + "\\"
    if not path.drive or ctypes.windll.kernel32.GetDriveTypeW(wintypes.LPCWSTR(drive)) != 3:
        raise ValueError("Solo se admiten discos locales fijos; no unidades de red.")
    return path


def inventory_folder(
    root: Path,
    cutoff: date,
    excluded_names: set[str] | None = None,
    excluded_extensions: set[str] | None = None,
    protected_names: set[str] | None = None,
) -> Inventory:
    """Scan without following symlinks, junctions or other reparse points.

    Caller must validate the root using validate_local_root before invocation.
    Folder names in exclusions/protection apply to matching descendants.
    """
    exclusions = {x.casefold() for x in (excluded_names or set()) if x}
    extensions = {("." + x.lstrip(".")).casefold() for x in (excluded_extensions or set()) if x}
    protected = {x.casefold() for x in (protected_names or set()) if x}
    result = Inventory(str(root), cutoff)
    stack: list[tuple[Path, bool]] = [(root, False)]
    while stack:
        directory, inherited_protection = stack.pop()
        try:
            with os.scandir(directory) as iterator:
                entries = list(iterator)
        except OSError as exc:
            result.errors.append(f"{directory}: {exc}")
            continue
        for entry in entries:
            path = Path(entry.path)
            try:
                attrs = entry.stat(follow_symlinks=False)
                if entry.is_symlink() or (getattr(attrs, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
                    result.errors.append(f"Enlace/punto de union omitido: {path}")
                    continue
                if entry.is_dir(follow_symlinks=False):
                    if entry.name.casefold() in exclusions:
                        result.excluded_dirs.append(str(path.relative_to(root)))
                    else:
                        stack.append((path, inherited_protection or entry.name.casefold() in protected))
                elif entry.is_file(follow_symlinks=False):
                    if path.suffix.casefold() in extensions:
                        result.excluded_files += 1
                        continue
                    modified = datetime.fromtimestamp(attrs.st_mtime)
                    created = datetime.fromtimestamp(attrs.st_ctime)
                    result.files.append(FileRecord(
                        relative_path=str(path.relative_to(root)),
                        name=entry.name,
                        extension=path.suffix.lower(),
                        size_bytes=attrs.st_size,
                        modified_at=modified,
                        created_at=created,
                        is_old=modified.date() <= cutoff,
                        protected=inherited_protection,
                    ))
            except OSError as exc:
                result.errors.append(f"{path}: {exc}")
    result.files.sort(key=lambda x: x.relative_path.casefold())
    return result
