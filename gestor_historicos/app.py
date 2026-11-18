"""Four-step Windows pilot UI. Source operations are strictly read-only."""
from __future__ import annotations
from datetime import date
from pathlib import Path
from queue import Empty, Queue
from threading import Event, Thread
import calendar
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .core import validate_local_root
from .storage import scan_to_sqlite, page, folder_summary, incidents_page


def years_before(today: date, years: int) -> date:
    target = today.year - years
    return today.replace(year=target, day=min(today.day, calendar.monthrange(target, today.month)[1]))


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MODAX | Gestor de Archivos Historicos - PILOTO LOCAL")
        self.geometry("1080x730")
        self.minsize(800, 550)
        self.root_path = tk.StringVar()
        self.years = tk.StringVar(value="5")
        self.cutoff = tk.StringVar(value=years_before(date.today(), 5).isoformat())
        self.exclusions = tk.StringVar()
        self.extensions = tk.StringVar()
        self.protections = tk.StringVar()
        self.search = tk.StringVar()
        self.only_old = tk.BooleanVar()
        self.status = tk.StringVar(value="Selecciona una carpeta local ficticia.")
        self.cancel_event = Event()
        self.messages = Queue()
        self.worker = None
        self.summary = None
        self.db = None
        self.offset = 0
        self.workspace = tempfile.TemporaryDirectory(prefix="modax_piloto_")
        self._build()
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.after(150, self.poll)

    def _build(self):
        main = ttk.Frame(self, padding=12)
        main.pack(fill="both", expand=True)
        ttk.Label(main, text="MODAX | PILOTO LOCAL - SOLO LECTURA",
                  font=("Segoe UI", 14, "bold")).pack(anchor="w")
        ttk.Label(main, text="No copia, mueve ni elimina archivos. Prohibido usar carpetas del servidor.").pack(anchor="w")
        self.tabs = ttk.Notebook(main)
        self.tabs.pack(fill="both", expand=True, pady=10)
        self.frames = [ttk.Frame(self.tabs, padding=12) for _ in range(4)]
        for frame, name in zip(self.frames, ("1. Configuracion", "2. Analisis", "3. Resultados", "4. Revision")):
            self.tabs.add(frame, text=name)
        self.build_config(self.frames[0])
        self.build_analysis(self.frames[1])
        self.build_results(self.frames[2])
        self.build_review(self.frames[3])
        ttk.Label(main, textvariable=self.status, wraplength=960).pack(anchor="w")

    def field(self, parent, label, variable):
        ttk.Label(parent, text=label).pack(anchor="w", pady=(9, 2))
        ttk.Entry(parent, textvariable=variable).pack(fill="x")

    def build_config(self, parent):
        ttk.Label(parent, text="Carpeta de prueba (disco local fijo)").pack(anchor="w")
        row = ttk.Frame(parent)
        row.pack(fill="x")
        ttk.Entry(row, textvariable=self.root_path).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Examinar", command=self.choose).pack(side="left", padx=6)
        ttk.Label(parent, text="Antiguedad").pack(anchor="w", pady=(12, 2))
        row = ttk.Frame(parent)
        row.pack(anchor="w")
        for years in ("3", "5", "7", "10"):
            ttk.Radiobutton(row, text=years + " anos", variable=self.years,
                            value=years, command=self.set_years).pack(side="left", padx=(0, 14))
        ttk.Radiobutton(row, text="Fecha manual", variable=self.years, value="manual").pack(side="left")
        self.field(parent, "Fecha de corte (AAAA-MM-DD; incluye el dia)", self.cutoff)
        self.field(parent, "Excluir carpetas por RUTA RELATIVA (separadas por coma)", self.exclusions)
        self.field(parent, "Excluir extensiones (ej.: .tmp,.bak)", self.extensions)
        self.field(parent, "Proteger carpetas por RUTA RELATIVA (separadas por coma)", self.protections)
        ttk.Label(parent, text="Ejemplo de ruta relativa: PROYECTO_A\\BORRADORES. No se admiten comodines.",
                  wraplength=850).pack(anchor="w", pady=8)
        ttk.Button(parent, text="Revisar configuracion y analizar", command=self.confirm_start).pack(anchor="w", pady=10)

    def build_analysis(self, parent):
        ttk.Label(parent, text="Analisis en curso", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        self.progress_text = tk.StringVar(value="Todavia no se inicio un analisis.")
        ttk.Label(parent, textvariable=self.progress_text).pack(anchor="w", pady=12)
        self.bar = ttk.Progressbar(parent, mode="indeterminate")
        self.bar.pack(fill="x")
        self.cancel_button = ttk.Button(parent, text="Cancelar analisis", command=self.cancel, state="disabled")
        self.cancel_button.pack(anchor="w", pady=12)
        ttk.Label(parent, text="El avance se expresa en carpetas y archivos procesados; no se inventa un porcentaje.",
                  wraplength=850).pack(anchor="w")

    def build_results(self, parent):
        controls = ttk.Frame(parent)
        controls.pack(fill="x")
        ttk.Label(controls, text="Buscar ruta:").pack(side="left")
        ttk.Entry(controls, textvariable=self.search, width=35).pack(side="left", padx=6)
        ttk.Checkbutton(controls, text="Solo antiguos", variable=self.only_old).pack(side="left", padx=6)
        ttk.Button(controls, text="Aplicar filtros", command=self.reset_page).pack(side="left")
        self.table = ttk.Treeview(parent, columns=("ruta", "mb", "mod", "old", "prot"), show="headings")
        for key, label, width in (("ruta", "Ruta relativa", 520), ("mb", "MB", 70),
                                  ("mod", "Modificado", 150), ("old", "Antiguo", 80),
                                  ("prot", "Protegido", 90)):
            self.table.heading(key, text=label)
            self.table.column(key, width=width)
        self.table.pack(fill="both", expand=True, pady=8)
        nav = ttk.Frame(parent)
        nav.pack(anchor="w")
        ttk.Button(nav, text="Anterior", command=self.previous_page).pack(side="left")
        ttk.Button(nav, text="Siguiente", command=self.next_page).pack(side="left", padx=8)
        self.page_text = tk.StringVar(value="Sin resultados")
        ttk.Label(nav, textvariable=self.page_text).pack(side="left")

    def build_review(self, parent):
        ttk.Label(parent, text="Resumen y revision de incidencias",
                  font=("Segoe UI", 13, "bold")).pack(anchor="w")
        self.review_text = tk.Text(parent, height=20, wrap="word", state="disabled")
        self.review_text.pack(fill="both", expand=True, pady=8)
        ttk.Label(parent, text="Exportacion Excel: pendiente de Entrega 1. No hay operaciones de copia ni borrado.").pack(anchor="w")

    @staticmethod
    def values(text):
        return {x.strip() for x in text.split(",") if x.strip()}

    def choose(self):
        selected = filedialog.askdirectory(title="Carpeta local ficticia")
        if selected:
            self.root_path.set(selected)

    def set_years(self):
        self.cutoff.set(years_before(date.today(), int(self.years.get())).isoformat())

    def confirm_start(self):
        if self.worker and self.worker.is_alive():
            messagebox.showwarning("Analisis activo", "Espera o cancela el analisis actual.")
            return
        try:
            root = validate_local_root(self.root_path.get())
            cutoff = date.fromisoformat(self.cutoff.get().strip())
        except (ValueError, OSError) as exc:
            messagebox.showerror("Configuracion invalida", str(exc))
            return
        excluded = self.values(self.exclusions.get())
        extensions = self.values(self.extensions.get())
        protected = self.values(self.protections.get())
        summary = (f"Origen: {root}\nFecha de corte: {cutoff}\n"
                   f"Carpetas excluidas: {', '.join(sorted(excluded)) or '(ninguna)'}\n"
                   f"Extensiones excluidas: {', '.join(sorted(extensions)) or '(ninguna)'}\n"
                   f"Carpetas protegidas: {', '.join(sorted(protected)) or '(ninguna)'}\n\n"
                   "El analisis solo lee archivos. ¿Continuar?")
        if not messagebox.askyesno("Confirmar analisis", summary):
            return
        self.cancel_event = Event()
        self.db = Path(self.workspace.name) / f"inventario_{__import__('uuid').uuid4().hex}.sqlite"
        self.summary = None
        self.cancel_button.configure(state="normal")
        self.bar.start(10)
        self.tabs.select(1)
        self.status.set("Analizando...")
        self.worker = Thread(target=self.scan_worker, args=(root, self.db, cutoff, excluded, extensions, protected), daemon=True)
        self.worker.start()

    def scan_worker(self, root, db, cutoff, excluded, extensions, protected):
        try:
            result = scan_to_sqlite(root, db, cutoff, excluded, extensions, protected,
                                    cancel=self.cancel_event,
                                    progress=lambda dirs, files: self.messages.put(("progress", (dirs, files))))
            self.messages.put(("done", result))
        except Exception as exc:
            self.messages.put(("error", str(exc)))

    def poll(self):
        try:
            while True:
                kind, data = self.messages.get_nowait()
                if kind == "progress":
                    self.progress_text.set(f"{data[0]} carpetas examinadas · {data[1]} archivos inventariados")
                elif kind == "done":
                    self.finish(data)
                elif kind == "error":
                    self.bar.stop()
                    self.cancel_button.configure(state="disabled")
                    self.status.set("Fallo de analisis: " + data)
        except Empty:
            pass
        self.after(150, self.poll)

    def cancel(self):
        self.cancel_event.set()
        self.status.set("Solicitando cancelacion segura...")

    def finish(self, result):
        self.summary = result
        self.bar.stop()
        self.cancel_button.configure(state="disabled")
        self.status.set(f"Analisis {result.status}: {result.files} archivos, {result.incidents} incidencias.")
        self.reset_page()
        folders = folder_summary(self.db)
        incidents = incidents_page(self.db)
        lines = [
            f"ESTADO: {result.status}",
            f"Raiz: {result.root}",
            f"Fecha de corte: {result.cutoff}",
            f"Archivos: {result.files}; antiguos: {result.old}; protegidos: {result.protected}",
            f"Tamano: {result.bytes_total / 1024**3:.3f} GB",
            f"Carpetas examinadas: {result.directories}; exclusiones: {result.exclusions}",
            f"Incidencias: {result.incidents}",
            "",
            "RESUMEN POR CARPETA (hasta 100 primeras):",
        ]
        for folder, count, size, old, prot in folders[:100]:
            label = "ANTIGUA" if old == count else "RECIENTE" if old == 0 else "MIXTA"
            lines.append(f"{folder}: {count} archivos, {size / 1048576:.2f} MB, {label}, {prot} protegidos")
        lines.append("\nINCIDENCIAS (hasta 100 primeras):")
        lines.extend(f"{path}: {detail}" for path, detail in incidents)
        self.review_text.configure(state="normal")
        self.review_text.delete("1.0", "end")
        self.review_text.insert("end", "\n".join(lines))
        self.review_text.configure(state="disabled")
        self.tabs.select(3 if result.status != "COMPLETO" else 2)

    def reset_page(self):
        self.offset = 0
        self.load_page()

    def load_page(self):
        if not self.summary:
            return
        rows = page(self.db, self.search.get(), self.only_old.get(), self.offset, 200)
        self.table.delete(*self.table.get_children())
        for rel, size, mod, old, protected in rows:
            self.table.insert("", "end", values=(rel, f"{size / 1048576:.2f}",
                              mod[:19].replace("T", " "), "Si" if old else "No",
                              "Si" if protected else "No"))
        self.page_text.set(f"Filas {self.offset + 1 if rows else 0}–{self.offset + len(rows)}; pagina de 200")

    def previous_page(self):
        self.offset = max(0, self.offset - 200)
        self.load_page()

    def next_page(self):
        if self.summary:
            rows = page(self.db, self.search.get(), self.only_old.get(), self.offset + 200, 1)
            if rows:
                self.offset += 200
                self.load_page()

    def close(self):
        if self.worker and self.worker.is_alive():
            messagebox.showinfo("Analisis activo", "Cancela el analisis y espera a que termine antes de cerrar.")
            self.cancel_event.set()
            return
        self.workspace.cleanup()
        self.destroy()


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
