"""Export inventory for review. Never interprets approvals or modifies source files."""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
import sqlite3

HEADERS = (
    "ID_ARCHIVO", "NOMBRE", "RUTA_ORIGINAL", "CARPETA_RELATIVA", "EXTENSIÓN",
    "TAMAÑO_MB", "FECHA_CREACIÓN", "FECHA_MODIFICACIÓN", "ANTIGÜEDAD",
    "CLASIFICACIÓN", "PROTEGIDO", "DECISIÓN", "RESPONSABLE", "FECHA_APROBACIÓN",
)


def export_inventory(db_path: str | Path, source_root: str | Path,
                     destination: str | Path, cutoff: str) -> int:
    """Writes a new XLSX outside source. Fails closed on incomplete scans at UI layer."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    from openpyxl.worksheet.datavalidation import DataValidation
    from .core import validate_local_root

    root = validate_local_root(source_root)
    destination = Path(destination).absolute()
    validate_local_root(destination.parent)
    if destination.suffix.lower() != ".xlsx":
        raise ValueError("La salida debe ser un archivo .xlsx")
    if destination.exists() or destination.resolve().is_relative_to(root.resolve()):
        raise ValueError("Destino existente o dentro de la carpeta de origen.")
    workbook = Workbook(write_only=False)
    folders = workbook.active
    folders.title = "Resumen carpetas"
    folders.append(("CARPETA_RELATIVA", "ARCHIVOS", "TAMAÑO_MB", "ANTIGUOS", "PROTEGIDOS", "CLASIFICACIÓN"))
    files = workbook.create_sheet("Inventario completo")
    files.append(HEADERS)
    count = 0
    with sqlite3.connect(f"file:{Path(db_path).as_posix()}?mode=ro", uri=True) as conn:
        for folder, total, size, old, protected in conn.execute(
            "SELECT parent_path,COUNT(*),SUM(size_bytes),SUM(old),SUM(protected) FROM files GROUP BY parent_path ORDER BY parent_path"
        ):
            classification = "ANTIGUA" if old == total else "RECIENTE" if old == 0 else "MIXTA"
            folders.append((folder, total, round(size / 1048576, 2), old, protected, classification))
        for relative, parent, name, ext, size, modified, created, old, protected in conn.execute(
            "SELECT relative_path,parent_path,name,extension,size_bytes,modified_at,created_at,old,protected FROM files ORDER BY relative_path"
        ):
            count += 1
            # Prevent spreadsheet formula injection in names and paths.
            def literal(value):
                return "'" + value if isinstance(value, str) and value.startswith(("=", "+", "-", "@")) else value
            files.append((count, literal(name), literal(str(root / relative)), literal(parent),
                          literal(ext), round(size / 1048576, 2), created, modified,
                          "ANTIGUO" if old else "RECIENTE",
                          "ANTIGUO" if old else "RECIENTE", "SI" if protected else "NO",
                          "PENDIENTE", "", ""))
    for sheet in (folders, files):
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
        for cell in sheet[1]:
            cell.font = Font(color="FFFFFF", bold=True)
            cell.fill = PatternFill("solid", fgColor="243447")
    validation = DataValidation(type="list", formula1='"APROBAR,NO APROBAR,PENDIENTE"', allow_blank=False)
    files.add_data_validation(validation)
    if count:
        validation.add(f"L2:L{count + 1}")
    workbook.save(destination)
    return count
