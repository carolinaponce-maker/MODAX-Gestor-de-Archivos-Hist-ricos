"""Inventario de solo lectura. Piloto restringido a discos locales Windows.

No contiene funciones de copia, movimiento, sobrescritura o eliminacion.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
import os
import stat
from threading import Event
from typing import Callable


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
    scanned_dirs: int = 0
    cancelled: bool = False

    @property
    def complete(self) -> bool:
        return not self.cancelled and not self.errors

    @property
    def status(self) -> str:
        if self.cancelled:
            return "CANCELADO"
        return "PARCIAL" if self.errors else "COMPLETO"

    @property
    def total_bytes(self) -> int:
        return sum(item.size_bytes for item in self.files)

    @property
    def old_count(self) -> int:
        return sum(item.is_old for item in self.files)


def validate_local_root(raw: str | Path) -> Path:
    """Rechaza UNC, discos no fijos y componentes junction/symlink.

    Este control se aplica tambien dentro del motor, no solo en la interfaz.
    La comprobacion de raiz no sustituye la autorizacion de Sistemas.
    """
    if os.name != "nt":
        raise ValueError("Este piloto solo se ejecuta en Windows.")
    raw = str(raw).strip()
    if not raw or raw.startswith(("\\\\", "//")):
        raise ValueError("No se permiten rutas de red.")
    path = Path(raw).absolute()
    if not path.drive:
        raise ValueError("La carpeta debe estar en un disco local.")
    import ctypes
    from ctypes import wintypes
    drive = path.drive + "\\"
    if ctypes.windll.kernel32.GetDriveTypeW(wintypes.LPCWSTR(drive)) != 3:
        raise ValueError("Solo se permiten discos locales fijos.")
    # Walk every ancestor before accepting the path, including the selected root.
    for part in reversed((path, *path.parents)):
        try:
            info = part.lstat()
        except OSError as exc:
            raise ValueError(f"Ruta inaccesible: {part}") from exc
        if stat.S_ISLNK(info.st_mode) or (
            getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
        ):
            raise ValueError(f"No se permiten enlaces ni puntos de union: {part}")
    if not path.is_dir():
        raise ValueError("Selecciona una carpeta existente.")
    return path


def inventory_folder(
    root: Path,
    cutoff: date,
    excluded_names: set[str] | None = None,
    excluded_extensions: set[str] | None = None,
    protected_names: set[str] | None = None,
    cancel: Event | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> Inventory:
    """Recorre sin seguir enlaces. Cualquier error deja el resultado PARCIAL.

    La API actual conserva registros en memoria: no apta aun para volumen real.
    La validacion de raiz es obligatoria incluso para llamadas sin interfaz.
    """
    root = validate_local_root(root)
    exclusions = {x.casefold() for x in (excluded_names or set()) if x}
    extensions = {("." + x.lstrip(".")).casefold() for x in (excluded_extensions or set()) if x}
    protected = {x.casefold() for x in (protected_names or set()) if x}
    result = Inventory(str(root), cutoff)
    stack: list[tuple[Path, bool]] = [(root, False)]
    while stack:
        if cancel is not None and cancel.is_set():
            result.cancelled = True
            break
        directory, inherited_protection = stack.pop()
        try:
            with os.scandir(directory) as iterator:
                result.scanned_dirs += 1
                for entry in iterator:
                    if cancel is not None and cancel.is_set():
                        result.cancelled = True
                        break
                    path = Path(entry.path)
                    try:
                        attrs = entry.stat(follow_symlinks=False)
                        if entry.is_symlink() or (
                            getattr(attrs, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
                        ):
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
                            result.files.append(FileRecord(
                                relative_path=str(path.relative_to(root)),
                                name=entry.name,
                                extension=path.suffix.lower(),
                                size_bytes=attrs.st_size,
                                modified_at=modified,
                                created_at=datetime.fromtimestamp(attrs.st_ctime),
                                is_old=modified.date() <= cutoff,
                                protected=inherited_protection,
                            ))
                    except OSError as exc:
                        result.errors.append(f"{path}: {exc}")
        except OSError as exc:
            result.errors.append(f"{directory}: {exc}")
        if progress is not None:
            progress(result.scanned_dirs, len(result.files))
        if result.cancelled:
            break
    result.files.sort(key=lambda item: item.relative_path.casefold())
    return result
