import os
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from threading import Event

from gestor_historicos.core import inventory_folder, validate_local_root


@unittest.skipUnless(os.name == "nt", "El motor piloto solo se ejecuta en Windows")
class InventoryTests(unittest.TestCase):
    def test_recursive_exclusion_protection_and_cutoff(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ("old", "protected", "skip"):
                (root / name).mkdir()
            old = root / "old" / "a.txt"
            old.write_text("historico", encoding="utf-8")
            timestamp = datetime(2018, 1, 1).timestamp()
            os.utime(old, (timestamp, timestamp))
            (root / "protected" / "b.txt").write_text("actual", encoding="utf-8")
            (root / "skip" / "c.txt").write_text("omitir", encoding="utf-8")
            (root / "x.tmp").write_text("omitir", encoding="utf-8")
            result = inventory_folder(root, date(2020, 1, 1),
                excluded_names={"skip"}, excluded_extensions={".tmp"},
                protected_names={"protected"})
            self.assertEqual(len(result.files), 2)
            self.assertEqual(result.old_count, 1)
            self.assertEqual(result.excluded_files, 1)
            self.assertEqual(len(result.excluded_dirs), 1)
            self.assertTrue(result.complete)
            self.assertTrue(next(f for f in result.files if f.name == "b.txt").protected)

    def test_cancel_before_scan(self):
        with tempfile.TemporaryDirectory() as temp:
            cancel = Event()
            cancel.set()
            result = inventory_folder(Path(temp), date(2020, 1, 1), cancel=cancel)
            self.assertEqual(result.status, "CANCELADO")
            self.assertEqual(result.scanned_dirs, 0)

    def test_direct_motor_rejects_unc(self):
        with self.assertRaises(ValueError):
            inventory_folder(Path("//server/share"), date(2020, 1, 1))

    def test_local_root_is_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(validate_local_root(temp), Path(temp).absolute())


class CrossPlatformTests(unittest.TestCase):
    def test_non_windows_rejected(self):
        if os.name != "nt":
            with self.assertRaises(ValueError):
                validate_local_root(".")


if __name__ == "__main__":
    unittest.main()
