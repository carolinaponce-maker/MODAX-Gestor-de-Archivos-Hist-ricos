"""Regresiones de exportacion con archivos ficticios, exclusivamente en Windows."""
import os
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

from gestor_historicos.storage import scan_to_sqlite
from gestor_historicos.export import export_inventory


@unittest.skipUnless(os.name == "nt", "Piloto solo Windows")
class ExportTests(unittest.TestCase):
    def test_empty_folders_age_and_no_overwrite(self):
        from openpyxl import load_workbook
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "origen"
            source.mkdir()
            (source / "VACIA").mkdir()
            old = source / "=formula.txt"
            old.write_text("contenido", encoding="utf-8")
            timestamp = datetime(2017, 5, 10).timestamp()
            os.utime(old, (timestamp, timestamp))
            db = base / "inventario.sqlite"
            result = scan_to_sqlite(source, db, date(2020, 1, 1))
            self.assertEqual(result.status, "COMPLETO")
            output = base / "reporte.xlsx"
            self.assertEqual(export_inventory(db, source, output, result.cutoff), 1)
            wb = load_workbook(output, read_only=True, data_only=False)
            folders = list(wb["Resumen carpetas"].values)
            self.assertTrue(any(row[0] == "VACIA" and row[1] == 0
                                and row[5] == "VACÍA" for row in folders))
            row = list(wb["Inventario completo"].values)[1]
            self.assertEqual(len(row), 14)
            self.assertIsInstance(row[8], (int, float))
            self.assertEqual(row[9], "ANTIGUO")
            self.assertNotEqual(row[1][0], "=")
            wb.close()
            original = output.read_bytes()
            with self.assertRaises(ValueError):
                export_inventory(db, source, output, result.cutoff)
            self.assertEqual(output.read_bytes(), original)

    def test_many_rows(self):
        from openpyxl import load_workbook
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "origen"
            source.mkdir()
            for i in range(1200):
                (source / f"archivo_{i:05}.txt").write_text("x")
            db = base / "inventario.sqlite"
            result = scan_to_sqlite(source, db, date(2020, 1, 1))
            output = base / "muchos.xlsx"
            self.assertEqual(export_inventory(db, source, output, result.cutoff), 1200)
            wb = load_workbook(output, read_only=True)
            self.assertEqual(sum(1 for _ in wb["Inventario completo"].values), 1201)
            wb.close()


if __name__ == "__main__":
    unittest.main()
