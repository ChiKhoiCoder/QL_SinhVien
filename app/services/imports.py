from __future__ import annotations

import csv
import io
import json
import sqlite3
import uuid
from datetime import date, datetime
from typing import Any

from openpyxl import load_workbook

from app.database.connection import get_connection

MAX_ROWS = 10_000

SPECS: dict[str, dict[str, Any]] = {
    "students": {"title": "Sinh viên", "headers": ["ma_sinh_vien", "ho_ten", "ngay_sinh", "gioi_tinh", "dia_chi", "dien_thoai", "email", "ma_lop", "nganh_hoc"], "required": ["ma_sinh_vien", "ho_ten"],
        "labels": ["Mã sinh viên", "Họ và tên", "Ngày sinh (YYYY-MM-DD)", "Giới tính", "Địa chỉ", "Điện thoại", "Email", "Mã lớp", "Ngành học"]},
    "classes": {"title": "Lớp học", "headers": ["ma_lop", "ten_lop", "nganh_hoc", "giao_vien_chu_nhiem"], "required": ["ma_lop", "ten_lop"],
        "labels": ["Mã lớp", "Tên lớp", "Ngành học", "Giáo viên chủ nhiệm"]},
    "subjects": {"title": "Môn học", "headers": ["ma_mon", "ten_mon", "tin_chi", "nganh_hoc"], "required": ["ma_mon", "ten_mon"],
        "labels": ["Mã môn", "Tên môn", "Tín chỉ (1-12)", "Ngành học"]},
    "grades": {"title": "Điểm", "headers": ["ma_sinh_vien", "ma_mon_hoac_ten_mon", "hoc_ky", "diem"], "required": ["ma_sinh_vien", "ma_mon_hoac_ten_mon", "diem"],
        "labels": ["Mã sinh viên", "Mã hoặc tên môn", "Học kỳ", "Điểm (0-10)"]},
    "attendance": {"title": "Điểm danh", "headers": ["ma_sinh_vien", "ngay_diem_danh", "trang_thai", "ma_mon", "ghi_chu"], "required": ["ma_sinh_vien", "ngay_diem_danh", "trang_thai"],
        "labels": ["Mã sinh viên", "Ngày (YYYY-MM-DD)", "Trạng thái", "Mã môn (không bắt buộc)", "Ghi chú"]},
}


def _cell_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def read_upload(filename: str, content: bytes, entity: str) -> list[dict[str, str]]:
    if entity not in SPECS:
        raise ValueError("Phân hệ nhập dữ liệu không hợp lệ.")
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if suffix == "csv":
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = content.decode("cp1258")
        rows = list(csv.reader(io.StringIO(text)))
    elif suffix in {"xlsx", "xlsm"}:
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        worksheet = workbook.active
        rows = list(worksheet.iter_rows(values_only=True))
        workbook.close()
    else:
        raise ValueError("Chỉ hỗ trợ tệp .xlsx, .xlsm hoặc .csv.")
    if not rows:
        raise ValueError("Tệp chưa có dữ liệu.")
    spec = SPECS[entity]
    headers = [_cell_text(value).lstrip("\ufeff").lower() for value in rows[0]]
    expected = spec["headers"]
    positions = {header: index for index, header in enumerate(headers) if header}
    if not all(header in positions for header in spec["required"]):
        raise ValueError("Thiếu cột bắt buộc. Hãy tải mẫu của phân hệ này để dùng đúng tên cột.")
    if len(rows) - 1 > MAX_ROWS:
        raise ValueError(f"Mỗi lần nhập tối đa {MAX_ROWS:,} dòng.")
    parsed: list[dict[str, str]] = []
    for cells in rows[1:]:
        values = [_cell_text(cells[positions[key]]) if key in positions and positions[key] < len(cells) else "" for key in expected]
        if not any(values):
            continue
        parsed.append(dict(zip(expected, values)))
    if not parsed:
        raise ValueError("Không tìm thấy dòng dữ liệu sau hàng tiêu đề.")
    return parsed


def create_preview(entity: str, rows: list[dict[str, str]]) -> str:
    batch_id = uuid.uuid4().hex
    with get_connection() as db:
        db.execute("DELETE FROM import_batches WHERE created_at < datetime('now','-1 day')")
        db.execute("INSERT INTO import_batches(id,entity,status) VALUES(?,?,'preview')", (batch_id, entity))
        seen: set[tuple[Any, ...]] = set()
        for number, row in enumerate(rows, start=2):
            error = validate_row(db, entity, row)
            fingerprint: tuple[Any, ...] | None = None
            if entity == "classes": fingerprint = (row.get("ma_lop", "").casefold(),)
            elif entity == "students": fingerprint = (row.get("ma_sinh_vien", "").casefold(),)
            elif entity == "subjects": fingerprint = (row.get("ma_mon", "").casefold(),)
            elif entity == "grades": fingerprint = (row.get("ma_sinh_vien", "").casefold(), row.get("ma_mon_hoac_ten_mon", "").casefold(), (row.get("hoc_ky", "") or "Học kỳ 1").casefold())
            elif entity == "attendance": fingerprint = (row.get("ma_sinh_vien", "").casefold(), row.get("ma_mon", "").casefold(), row.get("ngay_diem_danh", ""))
            if not error and fingerprint in seen:
                error = "Dòng trùng lặp trong chính tệp tải lên."
            if fingerprint is not None: seen.add(fingerprint)
            db.execute("INSERT INTO import_rows(batch_id,row_number,payload,error) VALUES(?,?,?,?)",
                       (batch_id, number, json.dumps(row, ensure_ascii=False), error))
    return batch_id


def validate_row(db: sqlite3.Connection, entity: str, row: dict[str, str]) -> str:
    def required(*keys: str) -> bool:
        return all(row.get(key, "").strip() for key in keys)
    if entity == "classes":
        if not required("ma_lop", "ten_lop"):
            return "Thiếu mã lớp hoặc tên lớp."
        if db.execute("SELECT 1 FROM classes WHERE code=?", (row["ma_lop"],)).fetchone():
            return "Mã lớp đã tồn tại."
        return ""
    if entity == "students":
        if not required("ma_sinh_vien", "ho_ten"):
            return "Thiếu mã sinh viên hoặc họ tên."
        if db.execute("SELECT 1 FROM students WHERE code=?", (row["ma_sinh_vien"],)).fetchone():
            return "Mã sinh viên đã tồn tại."
        gender = row.get("gioi_tinh", "")
        if gender and gender not in {"Nam", "Nữ", "Khác"}:
            return "Giới tính chỉ nhận Nam, Nữ hoặc Khác."
        if row.get("ngay_sinh"):
            try: date.fromisoformat(row["ngay_sinh"])
            except ValueError: return "Ngày sinh phải theo YYYY-MM-DD."
        if row.get("ma_lop") and not db.execute("SELECT 1 FROM classes WHERE code=?", (row["ma_lop"],)).fetchone():
            return f"Không tìm thấy mã lớp {row['ma_lop']}."
        return ""
    if entity == "subjects":
        if not required("ma_mon", "ten_mon"):
            return "Thiếu mã môn hoặc tên môn."
        if db.execute("SELECT 1 FROM subjects WHERE code=?", (row["ma_mon"],)).fetchone():
            return "Mã môn đã tồn tại."
        try: credits = int(row.get("tin_chi", "3") or "3")
        except ValueError: return "Tín chỉ cần là số nguyên."
        return "" if 1 <= credits <= 12 else "Tín chỉ cần từ 1 đến 12."
    if entity == "grades":
        if not required("ma_sinh_vien", "ma_mon_hoac_ten_mon", "diem"):
            return "Thiếu mã sinh viên, môn học hoặc điểm."
        student = db.execute("SELECT id FROM students WHERE code=?", (row["ma_sinh_vien"],)).fetchone()
        if not student: return f"Không tìm thấy sinh viên {row['ma_sinh_vien']}."
        subject = row["ma_mon_hoac_ten_mon"]
        exists = db.execute("SELECT name FROM subjects WHERE code=? OR name=?", (subject, subject)).fetchone()
        if not exists: return f"Không tìm thấy môn học {subject}. Hãy nhập mã hoặc tên môn đã khai báo."
        semester = row.get("hoc_ky", "") or "Học kỳ 1"
        try: score = float(row["diem"])
        except ValueError: return "Điểm cần là số từ 0 đến 10."
        if not 0 <= score <= 10: return "Điểm cần từ 0 đến 10."
        if db.execute("SELECT 1 FROM grades WHERE student_id=? AND subject=? AND semester=?",
                      (student["id"], exists["name"], semester)).fetchone(): return "Điểm môn này trong học kỳ đã tồn tại."
        return ""
    if entity == "attendance":
        if not required("ma_sinh_vien", "ngay_diem_danh", "trang_thai"):
            return "Thiếu mã sinh viên, ngày hoặc trạng thái."
        student = db.execute("SELECT id FROM students WHERE code=?", (row["ma_sinh_vien"],)).fetchone()
        if not student: return f"Không tìm thấy sinh viên {row['ma_sinh_vien']}."
        try: date.fromisoformat(row["ngay_diem_danh"])
        except ValueError: return "Ngày điểm danh phải theo YYYY-MM-DD."
        if row["trang_thai"] not in {"Có mặt", "Vắng", "Muộn", "Có phép"}:
            return "Trạng thái nhận Có mặt, Vắng, Muộn hoặc Có phép."
        subject_id = None
        if row.get("ma_mon"):
            subject = db.execute("SELECT id FROM subjects WHERE code=?", (row["ma_mon"],)).fetchone()
            if not subject: return f"Không tìm thấy mã môn {row['ma_mon']}."
            subject_id = subject["id"]
        if db.execute("SELECT 1 FROM attendance WHERE student_id=? AND subject_id IS ? AND attendance_date=?",
                      (student["id"], subject_id, row["ngay_diem_danh"])).fetchone():
            return "Bản ghi điểm danh cho ngày/môn này đã tồn tại."
        return ""
    return "Phân hệ không hỗ trợ nhập."


def preview_rows(batch_id: str) -> dict[str, Any] | None:
    with get_connection() as db:
        batch = db.execute("SELECT * FROM import_batches WHERE id=? AND status='preview'", (batch_id,)).fetchone()
        if not batch: return None
        rows = db.execute("SELECT row_number,payload,error FROM import_rows WHERE batch_id=? ORDER BY row_number", (batch_id,)).fetchall()
        items = [{"row_number": r["row_number"], "payload": json.loads(r["payload"]), "error": r["error"]} for r in rows]
        return {"id": batch_id, "entity": batch["entity"], "title": SPECS[batch["entity"]]["title"],
                "headers": SPECS[batch["entity"]]["headers"], "labels": SPECS[batch["entity"]]["labels"],
                "rows": items, "valid": sum(not r["error"] for r in items), "invalid": sum(bool(r["error"]) for r in items)}


def apply_import(batch_id: str) -> dict[str, int] | None:
    with get_connection() as db:
        batch = db.execute("SELECT * FROM import_batches WHERE id=? AND status='preview'", (batch_id,)).fetchone()
        if not batch: return None
        entity = batch["entity"]
        rows = db.execute("SELECT id,row_number,payload,error FROM import_rows WHERE batch_id=? ORDER BY row_number", (batch_id,)).fetchall()
        result = {"imported": 0, "skipped": 0}
        for staged in rows:
            row = json.loads(staged["payload"])
            error = validate_row(db, entity, row)
            if error:
                db.execute("UPDATE import_rows SET error=? WHERE id=?", (error, staged["id"]))
                result["skipped"] += 1
                continue
            try:
                if entity == "classes":
                    db.execute("INSERT INTO classes(code,name,major,homeroom_teacher) VALUES(?,?,?,?)",
                               (row["ma_lop"],row["ten_lop"],row.get("nganh_hoc", ""),row.get("giao_vien_chu_nhiem", "")))
                elif entity == "students":
                    cls = db.execute("SELECT id FROM classes WHERE code=?", (row.get("ma_lop", ""),)).fetchone() if row.get("ma_lop") else None
                    db.execute("""INSERT INTO students(code,full_name,birth_date,gender,address,phone,email,class_id,major)
                                  VALUES(?,?,?,?,?,?,?,?,?)""",(row["ma_sinh_vien"],row["ho_ten"],row.get("ngay_sinh", ""),row.get("gioi_tinh", ""),row.get("dia_chi", ""),row.get("dien_thoai", ""),row.get("email", ""),cls["id"] if cls else None,row.get("nganh_hoc", "")))
                elif entity == "subjects":
                    db.execute("INSERT INTO subjects(code,name,credits,major) VALUES(?,?,?,?)",
                               (row["ma_mon"],row["ten_mon"],int(row.get("tin_chi", "3") or "3"),row.get("nganh_hoc", "")))
                elif entity == "grades":
                    student = db.execute("SELECT id FROM students WHERE code=?", (row["ma_sinh_vien"],)).fetchone()
                    subject = db.execute("SELECT name FROM subjects WHERE code=? OR name=?",(row["ma_mon_hoac_ten_mon"],row["ma_mon_hoac_ten_mon"])).fetchone()
                    db.execute("INSERT INTO grades(student_id,subject,semester,score) VALUES(?,?,?,?)",
                               (student["id"],subject["name"],row.get("hoc_ky", "") or "Học kỳ 1",float(row["diem"])))
                elif entity == "attendance":
                    student = db.execute("SELECT id FROM students WHERE code=?", (row["ma_sinh_vien"],)).fetchone()
                    subject = db.execute("SELECT id FROM subjects WHERE code=?",(row.get("ma_mon", ""),)).fetchone() if row.get("ma_mon") else None
                    db.execute("INSERT INTO attendance(student_id,subject_id,attendance_date,status,note) VALUES(?,?,?,?,?)",
                               (student["id"],subject["id"] if subject else None,row["ngay_diem_danh"],row["trang_thai"],row.get("ghi_chu", "")))
                result["imported"] += 1
            except sqlite3.IntegrityError as exc:
                result["skipped"] += 1
                db.execute("UPDATE import_rows SET error=? WHERE id=?", ("Dữ liệu trùng hoặc không hợp lệ: " + str(exc), staged["id"]))
        db.execute("UPDATE import_batches SET status='completed' WHERE id=?", (batch_id,))
        return result


def make_template(entity: str) -> bytes:
    if entity not in SPECS: raise ValueError("Phân hệ không hợp lệ.")
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = SPECS[entity]["title"][:31]
    sheet.append(SPECS[entity]["headers"])
    sheet.append(["" for _ in SPECS[entity]["headers"]])
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="4361EE")
        cell.alignment = Alignment(horizontal="center")
    for column in sheet.columns:
        letter = column[0].column_letter
        sheet.column_dimensions[letter].width = max(18, max(len(str(cell.value or "")) for cell in column) + 3)
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()
