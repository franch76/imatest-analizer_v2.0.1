"""Tkinter GUI for Imatest SFRreg batch analysis."""

from __future__ import annotations

import sys
import logging
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter import simpledialog

ROOT_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)).resolve()
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.runner import run_analysis_split


class TextHandler(logging.Handler):
    def __init__(self, text_widget: tk.Text):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)

        def append():
            self.text_widget.configure(state="normal")
            self.text_widget.insert("end", msg + "\n")
            self.text_widget.see("end")
            self.text_widget.configure(state="disabled")

        self.text_widget.after(0, append)


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Imatest SFRreg Batch Analysis")
        self.geometry("900x700")

        self.before_path = tk.StringVar()
        self.after_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.input_mode = tk.StringVar(value="folder")
        self.exclude_missing_pairs = tk.BooleanVar(value=False)
        self.cancel_event = threading.Event()
        self.worker_thread: threading.Thread | None = None

        self._build_menu()
        self._build_layout()
        self._setup_logging()

    def _build_menu(self) -> None:
        menu = tk.Menu(self)
        help_menu = tk.Menu(menu, tearoff=0)
        help_menu.add_command(label="About", command=self._show_about)
        help_menu.add_command(label="Usage", command=self._show_usage)
        menu.add_cascade(label="Help", menu=help_menu)
        self.config(menu=menu)

    def _build_layout(self) -> None:
        container = ttk.Frame(self, padding=8)
        container.pack(fill="both", expand=True)

        input_frame = ttk.LabelFrame(container, text="Input", padding=8)
        input_frame.pack(fill="x")

        ttk.Label(input_frame, text="Before folder or JSON files").grid(row=0, column=0, sticky="w")
        ttk.Entry(input_frame, textvariable=self.before_path, width=70).grid(row=1, column=0, padx=(0, 8), sticky="we")
        ttk.Button(input_frame, text="Select", command=lambda: self._select_input("before")).grid(row=1, column=1, sticky="e")

        ttk.Label(input_frame, text="After folder or JSON files").grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(input_frame, textvariable=self.after_path, width=70).grid(row=3, column=0, padx=(0, 8), sticky="we")
        ttk.Button(input_frame, text="Select", command=lambda: self._select_input("after")).grid(row=3, column=1, sticky="e")

        mode_frame = ttk.Frame(input_frame)
        mode_frame.grid(row=4, column=0, columnspan=2, sticky="w", pady=(6, 0))
        ttk.Label(mode_frame, text="Comparison mode:").pack(side="left")
        ttk.Radiobutton(mode_frame, text="Folder scan", variable=self.input_mode, value="folder").pack(side="left", padx=(8, 0))
        ttk.Radiobutton(mode_frame, text="Selected files", variable=self.input_mode, value="files").pack(side="left", padx=(8, 0))

        ttk.Checkbutton(
            mode_frame,
            text="Exclude missing pairs (use only matched Before/After keys)",
            variable=self.exclude_missing_pairs,
        ).pack(side="left", padx=(12, 0))

        output_frame = ttk.LabelFrame(container, text="Output", padding=8)
        output_frame.pack(fill="x", pady=(8, 0))

        ttk.Label(output_frame, text="Output folder").grid(row=0, column=0, sticky="w")
        ttk.Entry(output_frame, textvariable=self.output_path, width=70).grid(row=1, column=0, padx=(0, 8), sticky="we")
        ttk.Button(output_frame, text="Select Folder", command=self._select_output).grid(row=1, column=1, sticky="e")
        ttk.Button(output_frame, text="Create Folder", command=self._create_output).grid(row=1, column=2, sticky="e")

        control_frame = ttk.LabelFrame(container, text="Execution", padding=8)
        control_frame.pack(fill="x", pady=(8, 0))

        ttk.Button(control_frame, text="Analyze", command=self._start).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(control_frame, text="Stop", command=self._stop).grid(row=0, column=1, padx=(0, 8))
        ttk.Button(control_frame, text="Exit", command=self._exit).grid(row=0, column=2)

        log_frame = ttk.LabelFrame(container, text="Progress Log", padding=8)
        log_frame.pack(fill="both", expand=True, pady=(8, 0))

        self.log_text = tk.Text(log_frame, height=20, state="disabled")
        self.log_text.pack(fill="both", expand=True)

        for frame in (input_frame, output_frame, control_frame, log_frame):
            frame.configure(relief="groove")

    def _setup_logging(self) -> None:
        handler = TextHandler(self.log_text)
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        root = logging.getLogger()
        root.setLevel(logging.INFO)
        root.handlers = [handler]

    def _show_about(self) -> None:
        messagebox.showinfo(
            "About",
            "Imatest SFRreg JSON batch analysis tool.\n"
            "Generates before/after comparison, repeatability metrics, charts, and reports.",
        )

    def _show_usage(self) -> None:
        messagebox.showinfo(
            "Usage",
            "1) Select Before and After input paths.\n"
            "2) Select or create output folder.\n"
            "3) Click 'Analyze' to run.",
        )

    def _select_input(self, phase: str) -> None:
        mode = self.input_mode.get()
        if mode == "files":
            title = "Select BEFORE JSON files" if phase == "before" else "Select AFTER JSON files"
            paths = filedialog.askopenfilenames(title=title, filetypes=[("JSON files", "*.json")])
            if paths:
                value = ";".join(paths)
                if phase == "before":
                    self.before_path.set(value)
                else:
                    self.after_path.set(value)
        else:
            title = "Select BEFORE folder" if phase == "before" else "Select AFTER folder"
            path = filedialog.askdirectory(title=title)
            if path:
                if phase == "before":
                    self.before_path.set(path)
                else:
                    self.after_path.set(path)

    def _select_output(self) -> None:
        path = filedialog.askdirectory(title="Select output folder")
        if path:
            self.output_path.set(path)

    def _create_output(self) -> None:
        base = filedialog.askdirectory(title="Select parent folder for output")
        if not base:
            return
        name = simpledialog.askstring("Folder Name", "Enter output folder name:", parent=self)
        if not name:
            return
        path = Path(base) / name
        path.mkdir(parents=True, exist_ok=True)
        self.output_path.set(str(path))

    def _start(self) -> None:
        if self.worker_thread and self.worker_thread.is_alive():
            messagebox.showwarning("Already Running", "Analysis is already in progress.")
            return

        before_path = self.before_path.get().strip()
        after_path = self.after_path.get().strip()
        output_path = self.output_path.get().strip()
        if not before_path or not after_path:
            messagebox.showerror("Input Required", "Select Before and After input folders or files.")
            return
        if not output_path:
            messagebox.showerror("Output Required", "Select or create an output folder.")
            return

        self.cancel_event.clear()
        self._log("Analysis started")

        def worker():
            try:
                if self.input_mode.get() == "files":
                    before_files = [Path(p) for p in before_path.split(";") if p.strip()]
                    after_files = [Path(p) for p in after_path.split(";") if p.strip()]
                    run_analysis_split(
                        before_files,
                        after_files,
                        Path(output_path),
                        self.cancel_event.is_set,
                        self.exclude_missing_pairs.get(),
                    )
                else:
                    run_analysis_split(
                        Path(before_path),
                        Path(after_path),
                        Path(output_path),
                        self.cancel_event.is_set,
                        self.exclude_missing_pairs.get(),
                    )
            except Exception as exc:
                logging.getLogger(__name__).exception("Analysis failed: %s", exc)
            finally:
                self._log("Analysis finished")
                self._notify_missing_pairs(Path(output_path))

        self.worker_thread = threading.Thread(target=worker, daemon=True)
        self.worker_thread.start()

    def _stop(self) -> None:
        if self.worker_thread and self.worker_thread.is_alive():
            self.cancel_event.set()
            self._log("Stop requested")
        else:
            self._log("No analysis is currently running")

    def _exit(self) -> None:
        if self.worker_thread and self.worker_thread.is_alive():
            if not messagebox.askyesno("Exit", "Analysis is running. Exit anyway?"):
                return
        self.destroy()

    def _log(self, message: str) -> None:
        logging.getLogger(__name__).info(message)

    def _notify_missing_pairs(self, output_path: Path) -> None:
        report_path = output_path / "missing_pairs_report.csv"
        if not report_path.exists() or report_path.stat().st_size == 0:
            return

        def show():
            messagebox.showwarning(
                "Missing Pair Warning",
                f"Before/After unmatched keys were found.\n{report_path}",
            )

        self.after(0, show)


if __name__ == "__main__":
    app = App()
    app.mainloop()
