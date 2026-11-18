"""Synthetic local fixtures for Windows pilot regression tests.

Never touches real corporate data or network paths.
"""
import os
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

from gestor_historicos.storage import scan_to_sqlite, page, folder_summary


@unittest.skipUnless(os.name == "nt", "Piloto solo Windows")
class SyntheticFixtureTests(unittest.TestCase):
    def test_nested_mixed_protected_and_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "origen"
            source.mkdir()
            (source / "2020").mkdir()
            (source / "2020" / "sub").mkdir()
            (source / "PROTEGIDA").mkdir()
            (source / "VACIA").mkdir()
            old = source / "2020" / "sub" / "viejo.txt"
            old.write_text("viejo", encoding="utf-8")
            ts = datetime(2017, 5, 10).timestamp()
            os.utime(old, (ts, ts))
            (source / "2020" / "nuevo.txt").write_text("nuevo", encoding="utf-8")
            (source / "PROTEGIDA" / "interno.txt").write_text("protegido", encoding="utf-8")
            (source / "suelto.txt").write_text("suelto", encoding="utf-8")
            db = base / "resultado.sqlite"
            result = scan_to_sqlite(source, db, date(2020, 1, 1), protected_paths={"PROTEGIDA"})
            self.assertEqual(result.status, "COMPLETO")
            self.assertEqual(result.files, 4)
            self.assertEqual(result.old, 1)
            self.assertEqual(result.protected, 1)
            self.assertEqual(len(page(db, search="viejo")), 1)
            self.assertEqual(len(page(db, old_only=True)), 1)
            # Known gap: empty folders are not yet included in folder_summary.
            self.assertNotIn("VACIA", {row[0] for row in folder_summary(db)})

    def test_excluded_relative_path_does_not_exclude_same_name_elsewhere(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "origen"
            for folder in ("a/skip", "b/skip"):
                path = source / folder
                path.mkdir(parents=True)
                (path / "file.txt").write_text("ok", encoding="utf-8")
            db = base / "resultado.sqlite"
            result = scan_to_sqlite(source, db, date(2020, 1, 1), excluded_paths={"a/skip"})
            self.assertEqual(result.files, 1)
            self.assertEqual(result.exclusions, 1)
            self.assertIn("b", page(db)[0][0])


if __name__ == "__main__":
    unittest.main()
