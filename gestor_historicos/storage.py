"""SQLite-backed read-only inventory for the local Windows pilot.

SQLite database is stored in a caller-selected temporary workspace, not in source.
The scan itself only reads source files. No copy, move or delete functions.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from threading import Event
from typing import Callable
import os
import sqlite3
import stat
import uuid

from .core import validate_local_root

SCHEMA = """
CREATE TABLE IF NOT EXISTS files(
 id INTEGER PRIMARY KEY,
 relative_path TEXT NOT NULL UNIQUE,
 parent_path TEXT NOT NULL,
 name TEXT NOT NULL,
 extension TEXT NOT NULL,
 size_bytes INTEGER NOT NULL,
 modified_at TEXT NOT NULL,
 created_at TEXT NOT NULL,
 old INTEGER NOT NULL,
 protected INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_files_parent ON files(parent_path);
CREATE INDEX IF NOT EXISTS idx_files_old ON files(old);
CREATE TABLE IF NOT EXISTS incidents(id INTEGER PRIMARY KEY, path TEXT, detail TEXT);
CREATE TABLE IF NOT EXISTS exclusions(path TEXT PRIMARY KEY, kind TEXT NOT NULL);
"""


@dataclass(frozen=True)
class ScanSummary:
    run_id: str
    root: str
    cutoff: str
    status: str
    files: int
    old: int
    protected: int
    bytes_total: int
    directories: int
    incidents: int
    exclusions: int


def _normalise_names(values: set[str] | None) -> set[str]:
    return {v.strip().casefold() for v in (values or set()) if v.strip()}


def _safe_relative_paths(values: set[str] | None) -> set[str]:
    result = set()
    for raw in values or set():
        v = raw.replace("/", "\\").strip("\\ ").casefold()
        if not v or v.startswith("\\") or any(p in ("", ".", "..") for p in v.split("\\")):
            raise ValueError("Ruta de exclusion/proteccion no valida")
        result.add(v)
    return result


def scan_to_sqlite(
    raw_root: str | Path,
    db_path: str | Path,
    cutoff: date,
    excluded_paths: set[str] | None = None,
    excluded_extensions: set[str] | None = None,
    protected_paths: set[str] | None = None,
    cancel: Event | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> ScanSummary:
    root = validate_local_root(raw_root)
    exclusions = _safe_relative_paths(excluded_paths)
    protections = _safe_relative_paths(protected_paths)
    extensions = {"." + x.lstrip(".").casefold() for x in (excluded_extensions or set()) if x.strip()}
    db = Path(db_path)
    if db.exists():
        raise ValueError("La base de inventario ya existe; no se sobrescribe.")
    # Validate destination before any filesystem write; reject network/reparse parents.
    # The UI creates its private temporary workspace beforehand.
    db_parent = validate_local_root(db.parent)
    if db.is_symlink():
        raise ValueError("No se permite un enlace como archivo de inventario.")
    # DB must not reside inside the source tree, including the root itself.
    if db.resolve().is_relative_to(root.resolve()):
        raise ValueError("El inventario no puede guardarse dentro del origen.")
    run_id = uuid.uuid4().hex
    files = old = protected_count = bytes_total = directories = incidents = excluded = 0
    status = "COMPLETO"
    conn = sqlite3.connect(db)
    try:
        conn.executescript(SCHEMA)
        stack = [(root, False)]
        while stack:
            if cancel is not None and cancel.is_set():
                status = "CANCELADO"
                break
            folder, inherited_protection = stack.pop()
            try:
                with os.scandir(folder) as entries:
                    directories += 1
                    for entry in entries:
                        if cancel is not None and cancel.is_set():
                            status = "CANCELADO"
                            break
                        path = Path(entry.path)
                        relative = str(path.relative_to(root))
                        key = relative.casefold()
                        try:
                            info = entry.stat(follow_symlinks=False)
                            if entry.is_symlink() or (
                                getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
                            ):
                                conn.execute("INSERT INTO incidents(path,detail) VALUES (?,?)", (relative, "Enlace o reparse point omitido"))
                                incidents += 1
                                continue
                            if entry.is_dir(follow_symlinks=False):
                                if key in exclusions:
                                    conn.execute("INSERT INTO exclusions(path,kind) VALUES (?,?)", (relative, "carpeta"))
                                    excluded += 1
                                else:
                                    stack.append((path, inherited_protection or key in protections))
                            elif entry.is_file(follow_symlinks=False):
                                if path.suffix.casefold() in extensions:
                                    excluded += 1
                                    continue
                                modified = datetime.fromtimestamp(info.st_mtime)
                                is_old = int(modified.date() <= cutoff)
                                is_protected = int(inherited_protection)
                                conn.execute(
                                    """INSERT INTO files(relative_path,parent_path,name,extension,size_bytes,
                                    modified_at,created_at,old,protected) VALUES (?,?,?,?,?,?,?,?,?)""",
                                    (relative, str(path.parent.relative_to(root)), entry.name, path.suffix.lower(),
                                     info.st_size, modified.isoformat(), datetime.fromtimestamp(info.st_ctime).isoformat(),
                                     is_old, is_protected))
                                files += 1
                                old += is_old
                                protected_count += is_protected
                                bytes_total += info.st_size
                        except (OSError, ValueError) as exc:
                            conn.execute("INSERT INTO incidents(path,detail) VALUES (?,?)", (relative, str(exc)))
                            incidents += 1
                    conn.commit()
            except OSError as exc:
                conn.execute("INSERT INTO incidents(path,detail) VALUES (?,?)", (str(folder), str(exc)))
                incidents += 1
                conn.commit()
            if progress:
                progress(directories, files)
            if status == "CANCELADO":
                break
        if incidents and status == "COMPLETO":
            status = "PARCIAL"
        conn.commit()
    finally:
        conn.close()
    return ScanSummary(run_id, str(root), cutoff.isoformat(), status, files, old,
                       protected_count, bytes_total, directories, incidents, excluded)


def page(db_path: str | Path, search: str = "", old_only: bool = False,
         offset: int = 0, limit: int = 200) -> list[tuple]:
    """Paginated, parameterised read-only query."""
    if not 1 <= limit <= 500 or offset < 0:
        raise ValueError("Paginacion fuera de rango")
    with sqlite3.connect(f"file:{Path(db_path).as_posix()}?mode=ro", uri=True) as conn:
        sql = "SELECT relative_path,size_bytes,modified_at,old,protected FROM files WHERE 1=1"
        args: list[object] = []
        if search:
            sql += " AND instr(lower(relative_path), ?) > 0"
            args.append(search.casefold())
        if old_only:
            sql += " AND old=1"
        sql += " ORDER BY relative_path COLLATE NOCASE LIMIT ? OFFSET ?"
        args.extend((limit, offset))
        return conn.execute(sql, args).fetchall()


def folder_summary(db_path: str | Path) -> list[tuple]:
    with sqlite3.connect(f"file:{Path(db_path).as_posix()}?mode=ro", uri=True) as conn:
        return conn.execute(
            """SELECT parent_path,COUNT(*),SUM(size_bytes),SUM(old),SUM(protected)
               FROM files GROUP BY parent_path ORDER BY parent_path COLLATE NOCASE"""
        ).fetchall()


def incidents_page(db_path: str | Path, limit: int = 100) -> list[tuple]:
    with sqlite3.connect(f"file:{Path(db_path).as_posix()}?mode=ro", uri=True) as conn:
        return conn.execute("SELECT path,detail FROM incidents ORDER BY id LIMIT ?", (limit,)).fetchall()
