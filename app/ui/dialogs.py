from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable


class RecordDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, title: str, fields: list[dict[str, Any]],
                 initial: dict[str, Any] | None, on_save: Callable[[dict[str, Any]], None]):
        super().__init__(parent)
        self.title(title)
        self.configure(bg="white")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.values: dict[str, tk.Variable] = {}
        self.fields = fields
        self.on_save = on_save
        initial = initial or {}
        self.geometry(f"500x{min(660, 160 + 60 * len(fields))}")
        frame = ttk.Frame(self, padding=24)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=title, style="DialogTitle.TLabel").pack(anchor="w", pady=(0, 6))
        ttk.Label(frame, text="Nhập thông tin vào các trường bên dưới.", style="Muted.TLabel").pack(anchor="w", pady=(0, 14))
        body = ttk.Frame(frame)
        body.pack(fill="both", expand=True)
        for index, field in enumerate(fields):
            key, label = field["key"], field["label"]
            ttk.Label(body, text=label, style="Field.TLabel").grid(row=index, column=0, sticky="w", pady=7, padx=(0, 12))
            if field.get("type") == "choice":
                variable = tk.StringVar(value=str(initial.get(key, field.get("default", "")) or ""))
                widget = ttk.Combobox(body, textvariable=variable, values=field.get("values", []), state="readonly")
            else:
                variable = tk.StringVar(value=str(initial.get(key, field.get("default", "")) or ""))
                widget = ttk.Entry(body, textvariable=variable)
            widget.grid(row=index, column=1, sticky="ew", pady=7, ipady=5)
            self.values[key] = variable
        body.columnconfigure(1, weight=1)
        footer = ttk.Frame(frame)
        footer.pack(fill="x", pady=(16, 0))
        ttk.Button(footer, text="Hủy", style="Secondary.TButton", command=self.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(footer, text="Lưu thông tin", style="Accent.TButton", command=self.save).pack(side="right")
        self.bind("<Return>", lambda _event: self.save())
        self.bind("<Escape>", lambda _event: self.destroy())
        self.focus_force()

    def save(self) -> None:
        self.on_save({key: var.get().strip() for key, var in self.values.items()})
