"""Interfaz de la primera entrega: analisis local, sin operaciones destructivas."""
from datetime import date, datetime
from pathlib import Path
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .core import inventory_folder, validate_local_root


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MODAX | Gestor Historicos - PILOTO LOCAL (solo lectura)")
        self.geometry("1000x640")
        self.root_path = tk.StringVar()
        self.cutoff = tk.StringVar(value=date(date.today().year - 5, date.today().month, min(date.today().day, 28)).isoformat())
        self.exclusions = tk.StringVar()
        self.extensions = tk.StringVar()
        self.protected = tk.StringVar()
        self.status = tk.StringVar(value="Selecciona una carpeta de prueba en un disco local.")
        self._build()

    def _build(self):
        frame = ttk.Frame(self, padding=16)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="PILOTO LOCAL - SOLO LECTURA", font=("Segoe UI", 15, "bold")).pack(anchor="w")
        ttk.Label(frame, text="No copia, mueve ni elimina archivos. No permite unidades de red.").pack(anchor="w", pady=(0, 12))
        row = ttk.Frame(frame)
        row.pack(fill="x")
        ttk.Entry(row, textvariable=self.root_path).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Elegir carpeta", command=self.choose).pack(side="left", padx=8)
        for label, variable in (
            ("Fecha de corte (AAAA-MM-DD; incluye ese dia)", self.cutoff),
            ("Excluir carpetas por nombre (separadas por coma)", self.exclusions),
            ("Excluir extensiones (.tmp,.bak)", self.extensions),
            ("Proteger carpetas por nombre (separadas por coma)", self.protected),
        ):
            ttk.Label(frame, text=label).pack(anchor="w", pady=(8, 0))
            ttk.Entry(frame, textvariable=variable).pack(fill="x")
        self.start_button = ttk.Button(frame, text="Analizar carpeta", command=self.start)
        self.start_button.pack(anchor="w", pady=12)
        columns = ("ruta", "tamano", "modificado", "antiguo", "protegido")
        self.table = ttk.Treeview(frame, columns=columns, show="headings")
        for key, title, width in (
            ("ruta", "Ruta relativa", 460), ("tamano", "MB", 80),
            ("modificado", "Modificado", 140), ("antiguo", "Antiguo", 80),
            ("protegido", "Protegido", 90),
        ):
            self.table.heading(key, text=title)
            self.table.column(key, width=width)
        self.table.pack(fill="both", expand=True)
        ttk.Label(frame, textvariable=self.status).pack(anchor="w", pady=(8, 0))

    def choose(self):
        chosen = filedialog.askdirectory(title="Seleccionar carpeta local de prueba")
        if chosen:
            self.root_path.set(chosen)

    @staticmethod
    def names(value):
        return {part.strip() for part in value.split(",") if part.strip()}

    def start(self):
        try:
            root = validate_local_root(self.root_path.get())
            cutoff = date.fromisoformat(self.cutoff.get().strip())
        except (ValueError, OSError) as exc:
            messagebox.showerror("Carpeta o fecha no valida", str(exc))
            return
        self.start_button.configure(state="disabled")
        self.status.set("Analizando... puede demorar con carpetas grandes.")
        args = (root, cutoff, self.names(self.exclusions.get()),
                self.names(self.extensions.get()), self.names(self.protected.get()))
        threading.Thread(target=self._worker, args=args, daemon=True).start()

    def _worker(self, *args):
        try:
            result = inventory_folder(*args)
            self.after(0, lambda: self.show_result(result))
        except Exception as exc:
            self.after(0, lambda error=str(exc): self.failed(error))

    def failed(self, error):
        self.start_button.configure(state="normal")
        self.status.set("Error: " + error)

    def show_result(self, result):
        self.table.delete(*self.table.get_children())
        # First delivery: capped preview, inventory counts remain complete.
        for item in result.files[:3000]:
            self.table.insert("", "end", values=(
                item.relative_path, f"{item.size_bytes / 1048576:.2f}",
                item.modified_at.strftime("%Y-%m-%d %H:%M"),
                "Si" if item.is_old else "No", "Si" if item.protected else "No",
            ))
        self.status.set(
            f"{len(result.files)} archivos | {result.old_count} antiguos | "
            f"{result.total_bytes / (1024**3):.3f} GB | "
            f"{len(result.excluded_dirs)} carpetas excluidas | "
            f"{result.excluded_files} archivos excluidos | "
            f"{len(result.errors)} incidencias. Vista: primeros 3000."
        )
        self.start_button.configure(state="normal")


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
