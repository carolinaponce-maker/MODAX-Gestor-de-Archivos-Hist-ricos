"""Exportacion informativa de inventarios; nunca modifica archivos de origen."""
from __future__ import annotations

from datetime import datetime
from contextlib import closing
from pathlib import Path
import os
import sqlite3
import tempfile

HEADERS = (
    "ID_ARCHIVO", "NOMBRE", "RUTA_ORIGINAL", "CARPETA_RELATIVA", "EXTENSIÓN",
    "TAMAÑO_MB", "FECHA_CREACIÓN", "FECHA_MODIFICACIÓN", "ANTIGÜEDAD",
    "CLASIFICACIÓN", "PROTEGIDO", "DECISIÓN", "RESPONSABLE", "FECHA_APROBACIÓN",
)


def _literal(value):
    """Evita que un nombre o ruta controlado por terceros se interprete como formula."""
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def _header(sheet, values):
    from openpyxl.cell import WriteOnlyCell
    from openpyxl.styles import Font, PatternFill

    cells = []
    for value in values:
        cell = WriteOnlyCell(sheet, value=value)
        cell.font = Font(color="FFFFFF", bold=True)
        cell.fill = PatternFill("solid", fgColor="243447")
        cells.append(cell)
    sheet.append(cells)


def export_inventory(db_path: str | Path, source_root: str | Path,
                     destination: str | Path, cutoff: str) -> int:
    """Exporta XLSX con memoria acotada y publicacion sin sobrescritura.

    ANTIGÜEDAD: años transcurridos desde la ultima modificacion hasta hoy.
    El corte se utiliza para la clasificacion calculada durante el escaneo.
    """
    from openpyxl import Workbook

    from .core import validate_local_root

    root = validate_local_root(source_root)
    destination = Path(destination).absolute()
    validate_local_root(destination.parent)
    if destination.suffix.lower() != ".xlsx":
        raise ValueError("La salida debe ser un archivo .xlsx")
    if destination.exists() or destination.resolve().is_relative_to(root.resolve()):
        raise ValueError("Destino existente o dentro de la carpeta de origen.")

    workbook = Workbook(write_only=True)
    folders = workbook.create_sheet("Resumen carpetas")
    files = workbook.create_sheet("Inventario completo")
    for sheet in (folders, files):
        sheet.freeze_panes = "A2"
    _header(folders, ("CARPETA_RELATIVA", "ARCHIVOS", "TAMAÑO_MB",
                      "ANTIGUOS", "PROTEGIDOS", "CLASIFICACIÓN"))
    _header(files, HEADERS)
    count = folder_count = 0
    today = datetime.now().date()
    with closing(sqlite3.connect(f"file:{Path(db_path).as_posix()}?mode=ro", uri=True)) as conn:
        for folder, total, size, old, protected in conn.execute(
            """SELECT d.path, COUNT(f.id), COALESCE(SUM(f.size_bytes),0),
                      COALESCE(SUM(f.old),0), COALESCE(SUM(f.protected),0)
               FROM directories d LEFT JOIN files f ON f.parent_path=d.path
               GROUP BY d.path ORDER BY d.path COLLATE NOCASE"""
        ):
            classification = ("VACÍA" if total == 0 else
                              "ANTIGUA" if old == total else
                              "RECIENTE" if old == 0 else "MIXTA")
            folders.append((_literal(folder), total, round(size / 1048576, 2),
                            old, protected, classification))
            folder_count += 1
        for relative, parent, name, ext, size, modified, created, old, protected in conn.execute(
            """SELECT relative_path,parent_path,name,extension,size_bytes,
                      modified_at,created_at,old,protected
               FROM files ORDER BY relative_path"""
        ):
            count += 1
            modified_dt = datetime.fromisoformat(modified)
            created_dt = datetime.fromisoformat(created)
            age_years = round((today - modified_dt.date()).days / 365.2425, 2)
            files.append((count, _literal(name), _literal(str(root / relative)),
                          _literal(parent), _literal(ext), round(size / 1048576, 2),
                          created_dt, modified_dt, age_years,
                          "ANTIGUO" if old else "RECIENTE",
                          "SI" if protected else "NO", "PENDIENTE", "", ""))
    folders.auto_filter.ref = f"A1:F{folder_count + 1}"
    files.auto_filter.ref = f"A1:N{count + 1}"
    # La exportacion del Modulo 1 es informativa: no permite aprobar decisiones.
    # Las validaciones editables se incorporaran en un modulo posterior.

    # Guardar en un temporal fuera del origen; enlace duro exclusivo evita
    # sobrescribir un archivo creado concurrentemente en el destino.
    fd, temporary = tempfile.mkstemp(prefix=".modax_export_", suffix=".xlsx",
                                     dir=destination.parent)
    os.close(fd)
    try:
        workbook.save(temporary)
        os.link(temporary, destination)  # FileExistsError si ya existe
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
    return count
