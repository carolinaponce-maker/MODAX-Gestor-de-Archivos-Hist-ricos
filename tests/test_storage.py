import os
import sqlite3
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from threading import Event

from gestor_historicos.storage import scan_to_sqlite, page, folder_summary, incidents_page


@unittest.skipUnless(os.name == "nt", "Piloto restringido a Windows")
class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / "origen"
        self.source.mkdir()
        self.db = self.base / "inventario.sqlite"

    def test_inventory_and_pagination(self):
        (self.source / "a").mkdir()
        (self.source / "a" / "old.txt").write_text("historico")
        (self.source / "b.txt").write_text("actual")
        summary = scan_to_sqlite(self.source, self.db, date(2020, 1, 1),
                                 protected_paths={"a"})
        self.assertEqual(summary.status, "COMPLETO")
        self.assertEqual(summary.files, 2)
        self.assertEqual(summary.protected, 1)
        self.assertEqual(len(page(self.db, limit=1)), 1)
        self.assertEqual(len(page(self.db, offset=1, limit=1)), 1)
        self.assertEqual(len(folder_summary(self.db)), 2)

    def test_cancellation(self):
        cancel = Event()
        cancel.set()
        summary = scan_to_sqlite(self.source, self.db, date(2020, 1, 1), cancel=cancel)
        self.assertEqual(summary.status, "CANCELADO")
        self.assertEqual(summary.files, 0)

    def test_db_cannot_be_inside_source(self):
        with self.assertRaises(ValueError):
            scan_to_sqlite(self.source, self.source / "inventario.sqlite", date(2020, 1, 1))

    def test_db_cannot_overwrite(self):
        self.db.write_text("existing")
        with self.assertRaises(ValueError):
            scan_to_sqlite(self.source, self.db, date(2020, 1, 1))
        self.assertEqual(self.db.read_text(), "existing")

    def test_invalid_relative_paths(self):
        with self.assertRaises(ValueError):
            scan_to_sqlite(self.source, self.db, date(2020, 1, 1), excluded_paths={"../escape"})

    def test_extensions_and_folder_exclusions(self):
        (self.source / "skip").mkdir()
        (self.source / "skip" / "a.txt").write_text("skip")
        (self.source / "keep.tmp").write_text("skip")
        (self.source / "keep.txt").write_text("keep")
        summary = scan_to_sqlite(self.source, self.db, date(2020, 1, 1),
                                 excluded_paths={"skip"}, excluded_extensions={".tmp"})
        self.assertEqual(summary.files, 1)
        self.assertEqual(summary.exclusions, 2)

    def test_direct_unc_rejected(self):
        with self.assertRaises(ValueError):
            scan_to_sqlite(Path("//server/share"), self.db, date(2020, 1, 1))

    def test_pagination_limits(self):
        with self.assertRaises(ValueError):
            page(self.db, limit=10000)


if __name__ == "__main__":
    unittest.main()
