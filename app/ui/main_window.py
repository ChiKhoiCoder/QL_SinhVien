from __future__ import annotations

import csv
import sqlite3
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from app.repositories.school_repository import SchoolRepository
from app.ui.dialogs import RecordDialog

BG = "#F4F7FB"
NAVY = "#13213A"
BLUE = "#4361EE"
TEXT = "#17243A"
MUTED = "#738096"
WHITE = "#FFFFFF"


class MainWindow(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Student Management | Quản lý sinh viên")
        self.geometry("1320x820")
        self.minsize(1060, 680)
        self.configure(bg=BG)
        self.current_page = "Tổng quan"
        self._setup_styles()
        self._build_shell()
        self.show_page("Tổng quan")

    def _setup_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("White.TFrame", background=WHITE)
        style.configure("TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=BG, foreground=MUTED, font=("Segoe UI", 9))
        style.configure("Title.TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 22, "bold"))
        style.configure("Section.TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 12, "bold"))
        style.configure("DialogTitle.TLabel", background=WHITE, foreground=TEXT, font=("Segoe UI", 16, "bold"))
        style.configure("Field.TLabel", background=WHITE, foreground=TEXT, font=("Segoe UI", 9, "bold"))
        style.configure("TEntry", fieldbackground=WHITE, padding=9, bordercolor="#E1E7F0")
        style.configure("TCombobox", fieldbackground=WHITE, padding=8)
        style.configure("Treeview", background=WHITE, fieldbackground=WHITE, foreground=TEXT,
                        rowheight=38, font=("Segoe UI", 9), borderwidth=0)
        style.configure("Treeview.Heading", background="#F7F9FC", foreground=MUTED,
                        font=("Segoe UI", 9, "bold"), relief="flat", padding=11)
        style.map("Treeview", background=[("selected", "#E8EDFF")], foreground=[("selected", TEXT)])
        style.configure("Accent.TButton", background=BLUE, foreground=WHITE,
                        font=("Segoe UI", 9, "bold"), padding=(14, 9), borderwidth=0)
        style.map("Accent.TButton", background=[("active", "#354FD2")])
        style.configure("Secondary.TButton", background="#EEF1F6", foreground=TEXT,
                        font=("Segoe UI", 9, "bold"), padding=(12, 9), borderwidth=0)
        style.configure("Nav.TButton", background=NAVY, foreground="#BBC6D8", anchor="w",
                        font=("Segoe UI", 10), padding=(18, 12), borderwidth=0)
        style.map("Nav.TButton", background=[("active", "#233451")], foreground=[("active", WHITE)])

    def _build_shell(self) -> None:
        self.sidebar = tk.Frame(self, bg=NAVY, width=245)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        brand = tk.Frame(self.sidebar, bg=NAVY)
        brand.pack(fill="x", padx=20, pady=(25, 35))
        tk.Label(brand, text="S", bg=BLUE, fg=WHITE, font=("Segoe UI", 16, "bold"),
                 width=2, height=1).pack(side="left", padx=(0, 11))
        tk.Label(brand, text="STUDENT\nMANAGEMENT", bg=NAVY, fg=WHITE,
                 justify="left", font=("Segoe UI", 11, "bold")).pack(side="left")
        tk.Label(self.sidebar, text="MENU CHÍNH", bg=NAVY, fg="#8190A8",
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=22, pady=(0, 8))
        self.nav_buttons: dict[str, tk.Button] = {}
        pages = [("Tổng quan", "▦"), ("Sinh viên", "♙"), ("Lớp học", "▤"), ("Quản lý điểm", "▧"), ("Thống kê", "◷")]
        for page, icon in pages:
            btn = tk.Button(self.sidebar, text=f"  {icon}    {page}", anchor="w", bg=NAVY, fg="#BBC6D8",
                            activebackground="#233451", activeforeground=WHITE, relief="flat", bd=0,
                            font=("Segoe UI", 10), padx=18, pady=12, cursor="hand2",
                            command=lambda name=page: self.show_page(name))
            btn.pack(fill="x", padx=10, pady=2)
            self.nav_buttons[page] = btn
        tk.Frame(self.sidebar, bg="#2A3850", height=1).pack(fill="x", side="bottom", padx=18, pady=(0, 82))
        tk.Label(self.sidebar, text="●  Quản trị viên\n    Hệ thống nội bộ", bg=NAVY, fg="#D5DCEA",
                 justify="left", font=("Segoe UI", 9), pady=20).pack(side="bottom", anchor="w", padx=22)

        self.main = tk.Frame(self, bg=BG)
        self.main.pack(side="left", fill="both", expand=True)
        topbar = tk.Frame(self.main, bg=WHITE, height=64)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)
        self.breadcrumb = tk.Label(topbar, text="Trang chủ  /  Tổng quan", bg=WHITE, fg=MUTED,
                                   font=("Segoe UI", 9))
        self.breadcrumb.pack(side="left", padx=30)
        tk.Label(topbar, text="●", bg=WHITE, fg="#28B487", font=("Segoe UI", 10)).pack(side="right", padx=(0, 28))
        tk.Label(topbar, text="Hệ thống đang hoạt động", bg=WHITE, fg=MUTED,
                 font=("Segoe UI", 9)).pack(side="right")
        self.content = tk.Frame(self.main, bg=BG)
        self.content.pack(fill="both", expand=True, padx=30, pady=25)

    def show_page(self, page: str) -> None:
        self.current_page = page
        for widget in self.content.winfo_children():
            widget.destroy()
        for name, button in self.nav_buttons.items():
            button.configure(bg="#233451" if name == page else NAVY, fg=WHITE if name == page else "#BBC6D8")
        self.breadcrumb.configure(text=f"Trang chủ  /  {page}")
        if page == "Tổng quan":
            self._dashboard()
        elif page == "Sinh viên":
            self._students_page()
        elif page == "Lớp học":
            self._classes_page()
        elif page == "Quản lý điểm":
            self._grades_page()
        else:
            self._reports_page()

    def _heading(self, title: str, subtitle: str, action: str | None = None, command: Any = None) -> None:
        row = tk.Frame(self.content, bg=BG)
        row.pack(fill="x", pady=(0, 20))
        left = tk.Frame(row, bg=BG)
        left.pack(side="left")
        ttk.Label(left, text=title, style="Title.TLabel").pack(anchor="w")
        ttk.Label(left, text=subtitle, style="Muted.TLabel").pack(anchor="w", pady=(4, 0))
        if action:
            ttk.Button(row, text=f"＋  {action}", style="Accent.TButton", command=command).pack(side="right", pady=7)

    def _card(self, parent: tk.Misc, label: str, value: str, note: str, accent: str) -> tk.Frame:
        card = tk.Frame(parent, bg=WHITE, highlightbackground="#E9EDF4", highlightthickness=1)
        tk.Frame(card, bg=accent, width=4).pack(side="left", fill="y")
        body = tk.Frame(card, bg=WHITE)
        body.pack(fill="both", expand=True, padx=17, pady=15)
        tk.Label(body, text=label.upper(), bg=WHITE, fg=MUTED, font=("Segoe UI", 8, "bold")).pack(anchor="w")
        tk.Label(body, text=value, bg=WHITE, fg=TEXT, font=("Segoe UI", 23, "bold")).pack(anchor="w", pady=(4, 0))
        tk.Label(body, text=note, bg=WHITE, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w", pady=(1, 0))
        return card

    def _table(self, parent: tk.Misc, columns: list[tuple[str, str, int]], height: int = 9) -> ttk.Treeview:
        wrapper = tk.Frame(parent, bg=WHITE, highlightbackground="#E9EDF4", highlightthickness=1)
        wrapper.pack(fill="both", expand=True)
        ids = [c[0] for c in columns]
        tree = ttk.Treeview(wrapper, columns=ids, show="headings", height=height, selectmode="browse")
        for key, label, width in columns:
            tree.heading(key, text=label)
            tree.column(key, width=width, minwidth=60, anchor="w", stretch=True)
        scrollbar = ttk.Scrollbar(wrapper, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        scrollbar.pack(side="right", fill="y", padx=(0, 5), pady=8)
        tree.tag_configure("odd", background="#FAFBFD")
        tree._wrapper = wrapper  # type: ignore[attr-defined]
        return tree

    @staticmethod
    def _fill(tree: ttk.Treeview, rows: list[dict[str, Any]], keys: list[str]) -> None:
        tree.delete(*tree.get_children())
        for index, row in enumerate(rows):
            tree.insert("", "end", iid=str(row["id"]), values=tuple(row.get(key, "") for key in keys),
                        tags=("odd",) if index % 2 else ())

    def _dashboard(self) -> None:
        self._heading("Tổng quan", "Chào mừng trở lại! Đây là tình hình hệ thống hôm nay.")
        data = SchoolRepository.dashboard()
        totals = data["totals"]
        cards = tk.Frame(self.content, bg=BG)
        cards.pack(fill="x", pady=(0, 22))
        for label, value, note, color in [
            ("Tổng sinh viên", totals["students"], "Hồ sơ đang quản lý", BLUE),
            ("Lớp học", totals["classes"], "Lớp đang hoạt động", "#18A889"),
            ("Môn / đầu điểm", totals["grades"], "Bản ghi kết quả", "#F3A640"),
            ("Nam / Nữ", f"{totals['male']} / {totals['female']}", "Cơ cấu sinh viên", "#9370DB"),
        ]:
            self._card(cards, label, str(value), note, color).pack(side="left", fill="both", expand=True, padx=(0, 12))
        split = tk.Frame(self.content, bg=BG)
        split.pack(fill="both", expand=True)
        left = tk.Frame(split, bg=BG)
        left.pack(side="left", fill="both", expand=True, padx=(0, 14))
        right = tk.Frame(split, bg=BG, width=340)
        right.pack(side="left", fill="both", expand=True)
        ttk.Label(left, text="Danh sách lớp", style="Section.TLabel").pack(anchor="w", pady=(0, 12))
        class_tree = self._table(left, [("code", "MÃ LỚP", 95), ("name", "TÊN LỚP", 150), ("major", "NGÀNH", 150),
                                         ("teacher", "GIÁO VIÊN CHỦ NHIỆM", 175), ("count", "SĨ SỐ", 65)], 9)
        for i, row in enumerate(data["classes"]):
            class_tree.insert("", "end", values=(row["code"], row["name"], row["major"], row["homeroom_teacher"], row["student_count"]),
                              tags=("odd",) if i % 2 else ())
        ttk.Label(right, text="Sinh viên mới", style="Section.TLabel").pack(anchor="w", pady=(0, 12))
        recent_tree = self._table(right, [("code", "MÃ SV", 80), ("name", "HỌ VÀ TÊN", 150), ("class", "LỚP", 120)], 9)
        for i, row in enumerate(data["recent"]):
            recent_tree.insert("", "end", values=(row["code"], row["full_name"], row["class_name"]), tags=("odd",) if i % 2 else ())

    def _toolbar(self, parent: tk.Misc, search_var: tk.StringVar, refresh: Any, placeholder: str,
                 add_command: Any, class_filter: bool = False) -> tuple[ttk.Combobox | None, ttk.Combobox | None]:
        bar = tk.Frame(parent, bg=WHITE, highlightbackground="#E9EDF4", highlightthickness=1)
        bar.pack(fill="x", pady=(0, 12))
        search = ttk.Entry(bar, textvariable=search_var, width=30)
        search.pack(side="left", padx=12, pady=10, ipady=3)
        search.insert(0, placeholder)
        search.bind("<FocusIn>", lambda _e: search.delete(0, "end") if search.get() == placeholder else None)
        search.bind("<KeyRelease>", lambda _e: refresh())
        class_combo = gender_combo = None
        if class_filter:
            class_combo = ttk.Combobox(bar, state="readonly", width=19)
            class_combo.pack(side="left", padx=7, pady=10)
            class_combo.bind("<<ComboboxSelected>>", lambda _e: refresh())
            gender_combo = ttk.Combobox(bar, state="readonly", values=["Tất cả giới tính", "Nam", "Nữ", "Khác"], width=16)
            gender_combo.current(0)
            gender_combo.pack(side="left", padx=7, pady=10)
            gender_combo.bind("<<ComboboxSelected>>", lambda _e: refresh())
        ttk.Button(bar, text="＋  Thêm mới", style="Accent.TButton", command=add_command).pack(side="right", padx=10, pady=7)
        return class_combo, gender_combo

    def _students_page(self) -> None:
        self._heading("Quản lý sinh viên", "Quản lý hồ sơ và thông tin sinh viên.", "Thêm sinh viên", self._add_student)
        search_var = tk.StringVar()
        filter_bar = tk.Frame(self.content, bg=WHITE, highlightbackground="#E9EDF4", highlightthickness=1)
        filter_bar.pack(fill="x", pady=(0, 12))
        search = ttk.Entry(filter_bar, textvariable=search_var, width=32)
        search.pack(side="left", padx=12, pady=10, ipady=3)
        search.insert(0, "Tìm theo mã hoặc họ tên...")
        search.bind("<FocusIn>", lambda _e: search.delete(0, "end") if search.get() == "Tìm theo mã hoặc họ tên..." else None)
        class_options = SchoolRepository.class_options()
        class_filter_var = tk.StringVar(value="Tất cả lớp")
        gender_filter_var = tk.StringVar(value="Tất cả giới tính")
        class_filter = ttk.Combobox(filter_bar, textvariable=class_filter_var, state="readonly", width=20,
                                    values=["Tất cả lớp"] + [f"{c['code']} — {c['name']}" for c in class_options])
        class_filter.pack(side="left", padx=7, pady=10)
        gender_filter = ttk.Combobox(filter_bar, textvariable=gender_filter_var, state="readonly", width=17,
                                     values=["Tất cả giới tính", "Nam", "Nữ", "Khác"])
        gender_filter.pack(side="left", padx=7, pady=10)
        tree = self._table(self.content, [("code", "MÃ SINH VIÊN", 115), ("full_name", "HỌ VÀ TÊN", 175),
            ("birth_date", "NGÀY SINH", 100), ("gender", "GIỚI TÍNH", 85), ("phone", "ĐIỆN THOẠI", 115),
            ("email", "EMAIL", 190), ("class_name", "LỚP", 140), ("major", "NGÀNH HỌC", 140)], 13)
        def refresh(*_args: Any) -> None:
            chosen_class = next((c for c in class_options
                                 if f"{c['code']} — {c['name']}" == class_filter_var.get()), None)
            gender = "" if gender_filter_var.get() == "Tất cả giới tính" else gender_filter_var.get()
            rows = SchoolRepository.list_students(search_var.get(), chosen_class["id"] if chosen_class else None, gender)
            self._fill(tree, rows, ["code", "full_name", "birth_date", "gender", "phone", "email", "class_name", "major"])
        search.bind("<KeyRelease>", refresh)
        class_filter.bind("<<ComboboxSelected>>", refresh)
        gender_filter.bind("<<ComboboxSelected>>", refresh)
        actions = tk.Frame(self.content, bg=BG)
        actions.pack(fill="x", pady=12)
        ttk.Button(actions, text="Sửa hồ sơ đã chọn", style="Secondary.TButton", command=lambda: self._edit_student(tree)).pack(side="left")
        ttk.Button(actions, text="Xóa sinh viên", style="Secondary.TButton", command=lambda: self._delete_selected(tree, SchoolRepository.delete_student, refresh, "sinh viên")).pack(side="left", padx=8)
        ttk.Button(actions, text="Xuất CSV", style="Secondary.TButton", command=lambda: self._export_students()).pack(side="right")
        refresh()

    def _student_fields(self) -> list[dict[str, Any]]:
        classes = SchoolRepository.class_options()
        class_labels = ["Không xếp lớp"] + [f"{row['code']} — {row['name']}" for row in classes]
        return [
            {"key": "code", "label": "Mã sinh viên *"}, {"key": "full_name", "label": "Họ và tên *"},
            {"key": "birth_date", "label": "Ngày sinh (YYYY-MM-DD)"},
            {"key": "gender", "label": "Giới tính", "type": "choice", "values": ["Nam", "Nữ", "Khác"]},
            {"key": "phone", "label": "Số điện thoại"}, {"key": "email", "label": "Email"},
            {"key": "address", "label": "Địa chỉ"}, {"key": "major", "label": "Ngành học"},
            {"key": "class_label", "label": "Lớp học", "type": "choice", "values": class_labels, "default": class_labels[0]},
        ]

    def _open_student_dialog(self, initial: dict[str, Any] | None = None, record_id: int | None = None,
                             refresh: Any = None) -> None:
        initial = dict(initial or {})
        classes = SchoolRepository.class_options()
        if initial.get("class_id"):
            match = next((c for c in classes if c["id"] == initial["class_id"]), None)
            initial["class_label"] = f"{match['code']} — {match['name']}" if match else "Không xếp lớp"
        else:
            initial["class_label"] = "Không xếp lớp"
        def save(data: dict[str, Any]) -> None:
            if not data["code"] or not data["full_name"]:
                messagebox.showwarning("Thiếu thông tin", "Mã sinh viên và họ tên là bắt buộc.", parent=self)
                return
            label = data.pop("class_label")
            selected = next((c for c in classes if f"{c['code']} — {c['name']}" == label), None)
            data["class_id"] = selected["id"] if selected else None
            try:
                SchoolRepository.save_student(data, record_id)
            except Exception as exc:
                messagebox.showerror("Không thể lưu", self._friendly_error(exc), parent=self)
                return
            dialog.destroy()
            if refresh:
                refresh()
        dialog = RecordDialog(self, "Cập nhật sinh viên" if record_id else "Thêm sinh viên mới", self._student_fields(), initial, save)

    def _add_student(self) -> None:
        self._open_student_dialog()

    def _edit_student(self, tree: ttk.Treeview) -> None:
        selected = tree.selection()
        if not selected:
            messagebox.showinfo("Chưa chọn sinh viên", "Vui lòng chọn một sinh viên trong danh sách.", parent=self)
            return
        row = next(r for r in SchoolRepository.list_students() if r["id"] == int(selected[0]))
        self._open_student_dialog(row, row["id"], lambda: self.show_page("Sinh viên"))

    def _classes_page(self) -> None:
        self._heading("Quản lý lớp học", "Theo dõi lớp, ngành đào tạo và sĩ số.", "Thêm lớp học", self._add_class)
        tree = self._table(self.content, [("code", "MÃ LỚP", 125), ("name", "TÊN LỚP", 190),
            ("major", "NGÀNH HỌC", 200), ("homeroom_teacher", "GIÁO VIÊN CHỦ NHIỆM", 220), ("student_count", "SĨ SỐ", 100)], 13)
        def refresh() -> None:
            self._fill(tree, SchoolRepository.list_classes(), ["code", "name", "major", "homeroom_teacher", "student_count"])
        actions = tk.Frame(self.content, bg=BG)
        actions.pack(fill="x", pady=12)
        ttk.Button(actions, text="Sửa lớp đã chọn", style="Secondary.TButton", command=lambda: self._edit_class(tree, refresh)).pack(side="left")
        ttk.Button(actions, text="Xóa lớp", style="Secondary.TButton", command=lambda: self._delete_selected(tree, SchoolRepository.delete_class, refresh, "lớp học")).pack(side="left", padx=8)
        refresh()

    def _open_class_dialog(self, initial: dict[str, Any] | None = None, record_id: int | None = None, refresh: Any = None) -> None:
        fields = [{"key": "code", "label": "Mã lớp *"}, {"key": "name", "label": "Tên lớp *"},
                  {"key": "major", "label": "Ngành học"}, {"key": "homeroom_teacher", "label": "Giáo viên chủ nhiệm"}]
        def save(data: dict[str, Any]) -> None:
            if not data["code"] or not data["name"]:
                messagebox.showwarning("Thiếu thông tin", "Mã lớp và tên lớp là bắt buộc.", parent=self)
                return
            try:
                SchoolRepository.save_class(data, record_id)
            except Exception as exc:
                messagebox.showerror("Không thể lưu", self._friendly_error(exc), parent=self)
                return
            dialog.destroy()
            if refresh:
                refresh()
        dialog = RecordDialog(self, "Cập nhật lớp học" if record_id else "Thêm lớp học", fields, initial, save)

    def _add_class(self) -> None:
        self._open_class_dialog()

    def _edit_class(self, tree: ttk.Treeview, refresh: Any) -> None:
        selected = tree.selection()
        if not selected:
            messagebox.showinfo("Chưa chọn lớp", "Vui lòng chọn một lớp trong danh sách.", parent=self)
            return
        row = next(r for r in SchoolRepository.list_classes() if r["id"] == int(selected[0]))
        self._open_class_dialog(row, row["id"], refresh)

    def _grades_page(self) -> None:
        self._heading("Quản lý điểm", "Theo dõi kết quả học tập và điểm trung bình theo học kỳ.", "Thêm điểm", self._add_grade)
        search_var = tk.StringVar()
        bar = tk.Frame(self.content, bg=WHITE, highlightbackground="#E9EDF4", highlightthickness=1)
        bar.pack(fill="x", pady=(0, 12))
        entry = ttk.Entry(bar, textvariable=search_var, width=34)
        entry.pack(side="left", padx=12, pady=10, ipady=3)
        entry.insert(0, "Tìm sinh viên hoặc môn học...")
        entry.bind("<FocusIn>", lambda _e: entry.delete(0, "end") if entry.get() == "Tìm sinh viên hoặc môn học..." else None)
        tree = self._table(self.content, [("code", "MÃ SV", 105), ("full_name", "HỌ VÀ TÊN", 190), ("subject", "MÔN HỌC", 190),
            ("semester", "HỌC KỲ", 120), ("score", "ĐIỂM", 80), ("average", "ĐIỂM TB KỲ", 110), ("rank", "XẾP LOẠI", 115)], 13)
        def refresh(*_args: Any) -> None:
            rows = SchoolRepository.list_grades(search_var.get())
            for row in rows:
                average = row["average"]
                row["score"] = f"{row['score']:.1f}"
                row["average"] = f"{average:.2f}" if average is not None else "—"
                row["rank"] = self._rank(average)
            self._fill(tree, rows, ["code", "full_name", "subject", "semester", "score", "average", "rank"])
        entry.bind("<KeyRelease>", refresh)
        actions = tk.Frame(self.content, bg=BG)
        actions.pack(fill="x", pady=12)
        ttk.Button(actions, text="Sửa điểm đã chọn", style="Secondary.TButton", command=lambda: self._edit_grade(tree, refresh)).pack(side="left")
        ttk.Button(actions, text="Xóa điểm", style="Secondary.TButton", command=lambda: self._delete_selected(tree, SchoolRepository.delete_grade, refresh, "điểm")).pack(side="left", padx=8)
        refresh()

    @staticmethod
    def _rank(average: float | None) -> str:
        if average is None: return "—"
        if average >= 8: return "Giỏi"
        if average >= 6.5: return "Khá"
        if average >= 5: return "Trung bình"
        return "Yếu"

    def _open_grade_dialog(self, initial: dict[str, Any] | None = None, record_id: int | None = None, refresh: Any = None) -> None:
        students = SchoolRepository.student_options()
        options = [f"{s['code']} — {s['full_name']}" for s in students]
        initial = dict(initial or {})
        student = next((s for s in students if s["id"] == initial.get("student_id")), None)
        if student:
            initial["student_label"] = f"{student['code']} — {student['full_name']}"
        fields = [{"key": "student_label", "label": "Sinh viên *", "type": "choice", "values": options},
                  {"key": "subject", "label": "Môn học *"},
                  {"key": "semester", "label": "Học kỳ", "default": "Học kỳ 1"},
                  {"key": "score", "label": "Điểm (0–10) *"}]
        def save(data: dict[str, Any]) -> None:
            selected = next((s for s in students if f"{s['code']} — {s['full_name']}" == data.pop("student_label")), None)
            if not selected or not data["subject"]:
                messagebox.showwarning("Thiếu thông tin", "Hãy chọn sinh viên và nhập môn học.", parent=self); return
            try:
                data.update(student_id=selected["id"], score=float(data["score"]))
                if not 0 <= data["score"] <= 10: raise ValueError("Điểm phải nằm trong khoảng 0 đến 10.")
                SchoolRepository.save_grade(data, record_id)
            except ValueError as exc:
                messagebox.showwarning("Điểm không hợp lệ", str(exc) or "Điểm phải là số từ 0 đến 10.", parent=self); return
            except Exception as exc:
                messagebox.showerror("Không thể lưu", self._friendly_error(exc), parent=self); return
            dialog.destroy()
            if refresh: refresh()
        dialog = RecordDialog(self, "Cập nhật điểm" if record_id else "Thêm điểm mới", fields, initial, save)

    def _add_grade(self) -> None:
        if not SchoolRepository.student_options():
            messagebox.showinfo("Chưa có sinh viên", "Hãy thêm sinh viên trước khi nhập điểm.", parent=self); return
        self._open_grade_dialog()

    def _edit_grade(self, tree: ttk.Treeview, refresh: Any) -> None:
        selected = tree.selection()
        if not selected:
            messagebox.showinfo("Chưa chọn điểm", "Vui lòng chọn một dòng điểm.", parent=self); return
        row = next(r for r in SchoolRepository.list_grades() if r["id"] == int(selected[0]))
        self._open_grade_dialog(row, row["id"], refresh)

    def _delete_selected(self, tree: ttk.Treeview, delete: Any, refresh: Any, label: str) -> None:
        selected = tree.selection()
        if not selected:
            messagebox.showinfo("Chưa chọn dữ liệu", "Vui lòng chọn một dòng trong danh sách.", parent=self); return
        if messagebox.askyesno("Xác nhận xóa", f"Bạn có chắc muốn xóa {label} này?", parent=self):
            try:
                delete(int(selected[0]))
                refresh()
            except Exception as exc:
                messagebox.showerror("Không thể xóa", self._friendly_error(exc), parent=self)

    def _reports_page(self) -> None:
        self._heading("Thống kê & báo cáo", "Tổng hợp nhanh dữ liệu sinh viên và kết quả học tập.")
        data = SchoolRepository.dashboard()
        totals = data["totals"]
        cards = tk.Frame(self.content, bg=BG); cards.pack(fill="x", pady=(0, 22))
        for label, value, note, color in [("Tổng sinh viên", totals["students"], "Tất cả hồ sơ", BLUE),
            ("Tổng lớp", totals["classes"], "Lớp đào tạo", "#18A889"), ("Nam", totals["male"], "Sinh viên nam", "#4EA5D9"),
            ("Nữ", totals["female"], "Sinh viên nữ", "#D97DA9")]:
            self._card(cards, label, str(value), note, color).pack(side="left", fill="both", expand=True, padx=(0, 12))
        ttk.Label(self.content, text="Sĩ số theo lớp", style="Section.TLabel").pack(anchor="w", pady=(8, 12))
        tree = self._table(self.content, [("code", "MÃ LỚP", 120), ("name", "TÊN LỚP", 220), ("major", "NGÀNH HỌC", 240),
                                          ("homeroom_teacher", "GIÁO VIÊN CHỦ NHIỆM", 230), ("student_count", "SĨ SỐ", 100)], 12)
        self._fill(tree, data["classes"], ["code", "name", "major", "homeroom_teacher", "student_count"])
        bar = tk.Frame(self.content, bg=BG); bar.pack(fill="x", pady=12)
        ttk.Button(bar, text="Xuất danh sách sinh viên ra CSV", style="Accent.TButton", command=self._export_students).pack(side="left")

    def _export_students(self) -> None:
        path = filedialog.asksaveasfilename(parent=self, title="Xuất danh sách sinh viên", defaultextension=".csv",
                    filetypes=[("CSV UTF-8", "*.csv")], initialfile="danh_sach_sinh_vien.csv")
        if not path: return
        rows = SchoolRepository.list_students()
        headers = ["Mã sinh viên", "Họ và tên", "Ngày sinh", "Giới tính", "Địa chỉ", "Điện thoại", "Email", "Lớp", "Ngành"]
        keys = ["code", "full_name", "birth_date", "gender", "address", "phone", "email", "class_name", "major"]
        try:
            with Path(path).open("w", newline="", encoding="utf-8-sig") as file:
                writer = csv.writer(file); writer.writerow(headers)
                writer.writerows([[row.get(key, "") or "" for key in keys] for row in rows])
            messagebox.showinfo("Xuất thành công", f"Đã xuất {len(rows)} sinh viên.\n{path}", parent=self)
        except OSError as exc:
            messagebox.showerror("Không thể xuất tệp", str(exc), parent=self)

    @staticmethod
    def _friendly_error(error: Exception) -> str:
        message = str(error).lower()
        if isinstance(error, (sqlite3.IntegrityError,)):
            if "unique" in message: return "Mã sinh viên, mã lớp hoặc tổ hợp sinh viên – môn học – học kỳ đã tồn tại."
            if "foreign key" in message: return "Dữ liệu liên quan không còn tồn tại. Hãy tải lại danh sách rồi thử lại."
            if "check constraint" in message: return "Dữ liệu không hợp lệ. Điểm phải từ 0 đến 10."
        return f"Đã xảy ra lỗi khi thao tác dữ liệu.\n{error}"

