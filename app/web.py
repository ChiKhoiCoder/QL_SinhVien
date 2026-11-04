from __future__ import annotations

import csv
import io
import sqlite3
from typing import Any
from functools import wraps

from flask import Flask, Response, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from app.database.schema import initialize_database
from app.repositories.school_repository import SchoolRepository
from app.services.imports import SPECS, apply_import, create_preview, make_template, preview_rows, read_upload

app = Flask(__name__)
app.secret_key = "student-management-local-app-change-before-deployment"
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def ensure_default_admin() -> None:
    from app.database.connection import get_connection
    with get_connection() as db:
        if not db.execute("SELECT 1 FROM users LIMIT 1").fetchone():
            db.execute("INSERT INTO users(username,password_hash,display_name,role) VALUES(?,?,?,?)",
                       ("admin", generate_password_hash("admin123"), "Quản trị viên", "admin"))


def _rank(average: float | None) -> str:
    if average is None:
        return "—"
    if average >= 8:
        return "Giỏi"
    if average >= 6.5:
        return "Khá"
    if average >= 5:
        return "Trung bình"
    return "Yếu"


def _error_message(exc: Exception) -> str:
    message = str(exc).lower()
    if isinstance(exc, sqlite3.IntegrityError):
        if "unique" in message:
            return "Mã sinh viên, mã lớp hoặc tổ hợp sinh viên – môn – học kỳ đã tồn tại."
        if "check constraint" in message:
            return "Điểm phải nằm trong khoảng từ 0 đến 10."
        return "Dữ liệu đang được tham chiếu hoặc không hợp lệ."
    return str(exc)


@app.post("/inline-update")
@login_required
def inline_update():
    entity = request.form.get("entity", "")
    record_id = request.form.get("record_id", type=int)
    field = request.form.get("field", "")
    value = request.form.get("value", "").strip()
    definitions = {
        "attendance": {"status": ("attendance", "status")},
        "grades": {"score": ("grades", "score")},
        "students": {"gender": ("students", "gender"), "class_id": ("students", "class_id"), "major": ("students", "major")},
        "classes": {"major": ("classes", "major"), "homeroom_teacher": ("classes", "homeroom_teacher")},
        "subjects": {"credits": ("subjects", "credits")},
    }
    target = definitions.get(entity, {}).get(field)
    if not target or not record_id:
        flash("Trường cần cập nhật không hợp lệ.", "error")
        return redirect(request.referrer or url_for("dashboard"))
    try:
        if entity == "attendance" and value not in {"Có mặt", "Vắng", "Muộn", "Có phép"}:
            raise ValueError("Trạng thái điểm danh không hợp lệ.")
        if entity == "grades":
            value = float(value)
            if not 0 <= value <= 10:
                raise ValueError("Điểm phải nằm trong khoảng từ 0 đến 10.")
        if entity == "students" and field == "gender" and value not in {"", "Nam", "Nữ", "Khác"}:
            raise ValueError("Giới tính không hợp lệ.")
        if entity == "students" and field == "class_id":
            if value:
                value = int(value)
                from app.database.connection import get_connection
                with get_connection() as db:
                    if not db.execute("SELECT 1 FROM classes WHERE id=?", (value,)).fetchone():
                        raise ValueError("Không tìm thấy lớp cần chuyển sinh viên vào.")
            else:
                value = None
        if entity == "subjects":
            value = int(value)
            if not 1 <= value <= 12:
                raise ValueError("Tín chỉ cần từ 1 đến 12.")
        table, column = target
        from app.database.connection import get_connection
        with get_connection() as db:
            if entity == "students" and field == "class_id":
                db.execute("""UPDATE students SET class_id=?,major=CASE WHEN trim(major)=''
                    THEN COALESCE((SELECT major FROM classes WHERE id=?),'') ELSE major END WHERE id=?""",
                           (value, value, record_id))
            else:
                db.execute(f"UPDATE {table} SET {column}=? WHERE id=?", (value, record_id))
        flash("Đã cập nhật nhanh thông tin.", "success")
    except (ValueError, TypeError) as exc:
        flash(str(exc), "error")
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/")
@login_required
def dashboard():
    return render_template("dashboard.html", page="Tổng quan", data=SchoolRepository.dashboard(),
                           settings=SchoolRepository.get_settings())


@app.route("/students")
@login_required
def students():
    classes = SchoolRepository.class_options()
    class_id = request.args.get("class_id", type=int)
    gender = request.args.get("gender", "")
    return render_template("students.html", page="Sinh viên", students=SchoolRepository.list_students(
        request.args.get("q", ""), class_id, gender), classes=classes, class_id=class_id,
        gender=gender, q=request.args.get("q", ""), settings=SchoolRepository.get_settings())


@app.route("/students/save", methods=["POST"])
@login_required
def save_student():
    data = {key: request.form.get(key, "").strip() for key in
            ("code", "full_name", "birth_date", "gender", "address", "phone", "email", "major")}
    data["class_id"] = request.form.get("class_id", type=int) or None
    record_id = request.form.get("id", type=int)
    if not data["code"] or not data["full_name"]:
        flash("Mã sinh viên và họ tên là bắt buộc.", "error")
    else:
        try:
            SchoolRepository.save_student(data, record_id)
            flash("Đã lưu thông tin sinh viên.", "success")
        except Exception as exc:
            flash(_error_message(exc), "error")
    return redirect(url_for("students"))


@app.post("/students/<int:record_id>/delete")
@login_required
def delete_student(record_id: int):
    SchoolRepository.delete_student(record_id)
    flash("Đã xóa sinh viên.", "success")
    return redirect(url_for("students"))


@app.route("/classes")
@login_required
def classes():
    return render_template("classes.html", page="Lớp học", classes=SchoolRepository.list_classes(), settings=SchoolRepository.get_settings())


@app.get("/classes/<int:class_id>")
@login_required
def class_detail(class_id: int):
    data = SchoolRepository.class_detail(class_id)
    if not data:
        flash("Không tìm thấy lớp học.", "error")
        return redirect(url_for("classes"))
    return render_template("class_detail.html", page=data["class"]["name"], data=data,
                           settings=SchoolRepository.get_settings())


@app.post("/classes/save")
@login_required
def save_class():
    data = {key: request.form.get(key, "").strip() for key in ("code", "name", "major", "homeroom_teacher")}
    record_id = request.form.get("id", type=int)
    if not data["code"] or not data["name"]:
        flash("Mã lớp và tên lớp là bắt buộc.", "error")
    else:
        try:
            SchoolRepository.save_class(data, record_id)
            flash("Đã lưu thông tin lớp học.", "success")
        except Exception as exc:
            flash(_error_message(exc), "error")
    return redirect(url_for("classes"))


@app.post("/classes/<int:record_id>/delete")
@login_required
def delete_class(record_id: int):
    SchoolRepository.delete_class(record_id)
    flash("Đã xóa lớp học. Hồ sơ sinh viên được giữ lại.", "success")
    return redirect(url_for("classes"))


@app.route("/grades")
@login_required
def grades():
    class_id = request.args.get("class_id", type=int)
    subject_id = request.args.get("subject_id", type=int)
    search = request.args.get("q", "")
    selected_class = next((c for c in SchoolRepository.class_options() if c["id"] == class_id), None)
    selected_subject = None
    roster = []
    if class_id and subject_id:
        selected_subject, roster = SchoolRepository.grade_roster(class_id, subject_id, search)
        if not selected_subject:
            subject_id = None
    for row in roster:
        row["rank"] = _rank(row["average"])
    return render_template("grades.html", page="Quản lý điểm", roster=roster,
                           students=SchoolRepository.student_options(), subjects=SchoolRepository.list_subjects(), classes=SchoolRepository.class_options(),
                           selected_class=selected_class, selected_subject=selected_subject,
                           class_id=class_id, subject_id=subject_id, q=search, settings=SchoolRepository.get_settings())


@app.post("/grades/save")
@login_required
def save_grade():
    record_id = request.form.get("id", type=int)
    try:
        data: dict[str, Any] = {"student_id": request.form.get("student_id", type=int),
            "subject": request.form.get("subject", "").strip(),
            "semester": request.form.get("semester", "Học kỳ 1").strip() or "Học kỳ 1",
            "score": float(request.form.get("score", ""))}
        if not data["student_id"] or not data["subject"]:
            raise ValueError("Hãy chọn sinh viên và nhập tên môn học.")
        if not 0 <= data["score"] <= 10:
            raise ValueError("Điểm phải nằm trong khoảng từ 0 đến 10.")
        SchoolRepository.save_grade(data, record_id)
        flash("Đã lưu kết quả học tập.", "success")
    except (ValueError, TypeError, Exception) as exc:
        flash(_error_message(exc), "error")
    return redirect(url_for("grades", q=request.form.get("q", ""), class_id=request.form.get("class_id", type=int),
                            subject_id=request.form.get("subject_id", type=int)))


@app.post("/grades/<int:record_id>/delete")
@login_required
def delete_grade(record_id: int):
    SchoolRepository.delete_grade(record_id)
    flash("Đã xóa điểm.", "success")
    return redirect(url_for("grades"))


@app.route("/reports")
@login_required
def reports():
    return render_template("reports.html", page="Thống kê và báo cáo", data=SchoolRepository.report_data(), settings=SchoolRepository.get_settings())


@app.route("/subjects")
@login_required
def subjects():
    return render_template("subjects.html", page="Quản lý môn học",
                           subjects=SchoolRepository.list_subjects(request.args.get("q", "")),
                           q=request.args.get("q", ""), settings=SchoolRepository.get_settings())


@app.post("/subjects/save")
@login_required
def save_subject():
    record_id = request.form.get("id", type=int)
    data = {"code": request.form.get("code", "").strip(), "name": request.form.get("name", "").strip(),
            "major": request.form.get("major", "").strip()}
    try:
        data["credits"] = int(request.form.get("credits", "3"))
        if not data["code"] or not data["name"]:
            raise ValueError("Mã môn và tên môn là bắt buộc.")
        if not 1 <= data["credits"] <= 12:
            raise ValueError("Số tín chỉ cần từ 1 đến 12.")
        SchoolRepository.save_subject(data, record_id)
        flash("Đã lưu thông tin môn học.", "success")
    except Exception as exc:
        flash(_error_message(exc), "error")
    return redirect(url_for("subjects"))


@app.post("/subjects/<int:record_id>/delete")
@login_required
def delete_subject(record_id: int):
    SchoolRepository.delete_subject(record_id)
    flash("Đã xóa môn học. Các điểm đã nhập vẫn được giữ.", "success")
    return redirect(url_for("subjects"))


@app.route("/attendance")
@login_required
def attendance():
    subjects = SchoolRepository.list_subjects()
    search = request.args.get("q", "")
    class_id = request.args.get("class_id", type=int)
    attendance_date = request.args.get("attendance_date", "").strip() or __import__("datetime").date.today().isoformat()
    subject_id = request.args.get("subject_id", type=int)
    data = SchoolRepository.attendance_data(search, request.args.get("status", ""),
                                             subject_id,
                                             class_id)
    roster = SchoolRepository.attendance_roster(search, class_id, attendance_date, subject_id)
    return render_template("attendance.html", page="Quản lý điểm danh", data=data, subjects=subjects,
                           students=SchoolRepository.student_options(), roster=roster, q=search,
                           status=request.args.get("status", ""), subject_id=request.args.get("subject_id", type=int),
                           classes=SchoolRepository.class_options(), class_id=class_id,
                           today=__import__("datetime").date.today().isoformat(), attendance_date=attendance_date,
                           settings=SchoolRepository.get_settings())


@app.post("/attendance/quick-save")
@login_required
def quick_save_attendance():
    student_id = request.form.get("student_id", type=int)
    attendance_date = request.form.get("attendance_date", "").strip()
    status = request.form.get("status", "").strip()
    subject_id = request.form.get("subject_id", type=int) or None
    try:
        if not student_id or status not in {"Có mặt", "Vắng", "Muộn", "Có phép"}:
            raise ValueError("Hãy chọn trạng thái điểm danh hợp lệ.")
        SchoolRepository.quick_save_attendance(student_id, subject_id, attendance_date, status)
        flash("Đã lưu trạng thái điểm danh.", "success")
    except Exception as exc:
        flash(_error_message(exc), "error")
    return redirect(url_for("attendance", q=request.form.get("q", ""), class_id=request.form.get("class_id", type=int),
                            subject_id=subject_id, attendance_date=attendance_date))


@app.post("/attendance/save")
@login_required
def save_attendance():
    record_id = request.form.get("id", type=int)
    data = {"student_id": request.form.get("student_id", type=int),
            "subject_id": request.form.get("subject_id", type=int) or None,
            "attendance_date": request.form.get("attendance_date", "").strip(),
            "status": request.form.get("status", "").strip(), "note": request.form.get("note", "").strip()}
    if not data["student_id"] or not data["attendance_date"] or data["status"] not in ["Có mặt", "Vắng", "Muộn", "Có phép"]:
        flash("Hãy chọn sinh viên, ngày và trạng thái điểm danh hợp lệ.", "error")
    else:
        try:
            SchoolRepository.save_attendance(data, record_id)
            flash("Đã lưu điểm danh.", "success")
        except Exception as exc:
            flash(_error_message(exc), "error")
    return redirect(url_for("attendance"))


@app.post("/attendance/<int:record_id>/delete")
@login_required
def delete_attendance(record_id: int):
    SchoolRepository.delete_attendance(record_id)
    flash("Đã xóa bản ghi điểm danh.", "success")
    return redirect(url_for("attendance"))


@app.route("/settings")
@login_required
def settings():
    return render_template("settings.html", page="Cài đặt", settings=SchoolRepository.get_settings(),
                           display_name=session.get("display_name", "Quản trị viên"),
                           theme=request.args.get("tab", "appearance"))


@app.route("/support", methods=["GET", "POST"])
@login_required
def support():
    from app.database.connection import get_connection
    if request.method == "POST":
        action = request.form.get("action", "create")
        if action == "create":
            title = request.form.get("title", "").strip()
            category = request.form.get("category", "Lỗi chức năng").strip()
            priority = request.form.get("priority", "Trung bình").strip()
            description = request.form.get("description", "").strip()
            if not title or not description:
                flash("Hãy nhập tiêu đề và mô tả sự cố.", "error")
            elif priority not in {"Thấp", "Trung bình", "Cao", "Khẩn cấp"}:
                flash("Mức độ ưu tiên không hợp lệ.", "error")
            else:
                with get_connection() as db:
                    db.execute("INSERT INTO support_tickets(title,category,priority,description,reporter_id) VALUES(?,?,?,?,?)",
                               (title, category, priority, description, session["user_id"]))
                flash("Đã gửi sự cố. Bộ phận quản trị sẽ tiếp nhận xử lý.", "success")
            return redirect(url_for("support"))
        if action == "update":
            ticket_id = request.form.get("ticket_id", type=int)
            status = request.form.get("status", "").strip()
            note = request.form.get("resolution_note", "").strip()
            if session.get("role") != "admin":
                flash("Chỉ quản trị viên mới có thể cập nhật trạng thái.", "error")
            elif status not in {"Mới tiếp nhận", "Đang xử lý", "Chờ phản hồi", "Đã giải quyết"}:
                flash("Trạng thái xử lý không hợp lệ.", "error")
            else:
                with get_connection() as db:
                    db.execute("UPDATE support_tickets SET status=?,resolution_note=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                               (status, note, ticket_id))
                flash("Đã cập nhật tiến độ sự cố.", "success")
            return redirect(url_for("support"))
    with get_connection() as db:
        query = """SELECT t.*,u.display_name AS reporter_name FROM support_tickets t
                   JOIN users u ON u.id=t.reporter_id ORDER BY
                   CASE t.status WHEN 'Mới tiếp nhận' THEN 0 WHEN 'Đang xử lý' THEN 1 WHEN 'Chờ phản hồi' THEN 2 ELSE 3 END,
                   t.created_at DESC"""
        tickets = db.execute(query).fetchall()
        counts = {row["status"]: row["total"] for row in db.execute(
            "SELECT status,COUNT(*) AS total FROM support_tickets GROUP BY status").fetchall()}
    return render_template("support.html", page="Tiếp nhận sự cố", tickets=tickets, counts=counts,
                           is_admin=session.get("role") == "admin", settings=SchoolRepository.get_settings())


@app.post("/settings/general")
@login_required
def save_general_settings():
    values = {
        "institution_name": request.form.get("institution_name", "").strip() or "Student Management",
        "academic_year": request.form.get("academic_year", "").strip() or "2026–2027",
        "default_semester": request.form.get("default_semester", "Học kỳ 1").strip() or "Học kỳ 1",
        "items_per_page": request.form.get("items_per_page", "20"),
        "allow_csv_export": "1" if request.form.get("allow_csv_export") in {"1", "on"} else "0",
        "theme": request.form.get("theme", "light") if request.form.get("theme") in {"light", "dark"} else "light",
        "accent_color": request.form.get("accent_color", "blue") if request.form.get("accent_color") in {"blue", "green", "violet", "orange", "rose"} else "blue",
        "font_scale": request.form.get("font_scale", "normal") if request.form.get("font_scale") in {"small", "normal", "large"} else "normal",
        "compact_tables": "1" if request.form.get("compact_tables") in {"1", "on"} else "0",
        "show_dashboard_banner": "1" if request.form.get("show_dashboard_banner") in {"1", "on"} else "0",
    }
    if values["items_per_page"] not in {"10", "20", "50", "100"}:
        values["items_per_page"] = "20"
    SchoolRepository.save_settings(values)
    flash("Đã lưu cài đặt hệ thống.", "success")
    return redirect(url_for("settings", tab="appearance"))


@app.post("/settings/account")
@login_required
def save_account_settings():
    from app.database.connection import get_connection
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")
    display_name = request.form.get("display_name", "").strip()
    with get_connection() as db:
        user = db.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    if not display_name:
        flash("Tên hiển thị không được để trống.", "error")
    elif new_password and (not check_password_hash(user["password_hash"], current_password)):
        flash("Mật khẩu hiện tại chưa chính xác.", "error")
    elif new_password and len(new_password) < 8:
        flash("Mật khẩu mới cần có ít nhất 8 ký tự.", "error")
    elif new_password and new_password != confirm_password:
        flash("Mật khẩu xác nhận không khớp.", "error")
    else:
        password_hash = generate_password_hash(new_password) if new_password else None
        SchoolRepository.update_account(session["user_id"], display_name, password_hash)
        session["display_name"] = display_name
        flash("Đã cập nhật hồ sơ quản trị." if not new_password else "Đã cập nhật hồ sơ và mật khẩu.", "success")
    return redirect(url_for("settings", tab="account"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        from app.database.connection import get_connection
        with get_connection() as db:
            user = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["display_name"] = user["display_name"]
            session["role"] = user["role"]
            next_url = request.args.get("next", "")
            if not next_url.startswith("/") or next_url.startswith("//"):
                next_url = url_for("dashboard")
            return redirect(next_url)
        flash("Tên đăng nhập hoặc mật khẩu chưa chính xác.", "error")
    return render_template("login.html", page="Đăng nhập")


@app.post("/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/students/export")
@login_required
def export_students():
    if SchoolRepository.get_settings()["allow_csv_export"] != "1":
        flash("Chức năng xuất CSV hiện đã tắt trong cài đặt.", "error")
        return redirect(request.referrer or url_for("students"))
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Mã sinh viên", "Họ và tên", "Ngày sinh", "Giới tính", "Địa chỉ", "Điện thoại", "Email", "Lớp", "Ngành"])
    keys = ["code", "full_name", "birth_date", "gender", "address", "phone", "email", "class_name", "major"]
    for row in SchoolRepository.list_students():
        writer.writerow([row.get(key, "") or "" for key in keys])
    return Response("\ufeff" + output.getvalue(), mimetype="text/csv; charset=utf-8",
                    headers={"Content-Disposition": "attachment; filename=danh_sach_sinh_vien.csv"})


@app.route("/imports/<entity>", methods=["GET", "POST"])
@login_required
def imports(entity: str):
    if entity not in SPECS:
        return redirect(url_for("dashboard"))
    spec = SPECS[entity]
    if request.method == "POST":
        action = request.form.get("action", "preview")
        if action == "apply":
            result = apply_import(request.form.get("batch_id", ""))
            if result is None:
                flash("Phiên xem trước không còn hiệu lực. Hãy tải lại tệp để xem trước lại.", "error")
            else:
                flash(f"Đã nhập {result['imported']} dòng; bỏ qua {result['skipped']} dòng lỗi hoặc trùng.",
                      "success" if result["imported"] else "error")
            return redirect(url_for("imports", entity=entity))
        uploaded = request.files.get("file")
        if not uploaded or not uploaded.filename:
            flash("Hãy chọn tệp Excel hoặc CSV cần tải lên.", "error")
            return redirect(url_for("imports", entity=entity))
        try:
            rows = read_upload(uploaded.filename, uploaded.read(), entity)
            batch_id = create_preview(entity, rows)
            return redirect(url_for("imports", entity=entity, batch=batch_id))
        except Exception as exc:
            flash(str(exc), "error")
    preview = preview_rows(request.args.get("batch", "")) if request.method == "GET" else None
    return render_template("imports.html", page=f"Nhập {spec['title']}", entity=entity, spec=spec,
                           preview=preview, settings=SchoolRepository.get_settings())


@app.get("/imports/<entity>/template")
@login_required
def import_template(entity: str):
    if entity not in SPECS:
        return redirect(url_for("dashboard"))
    filename = f"mau_nhap_{entity}.xlsx"
    return Response(make_template(entity), mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f"attachment; filename={filename}"})


initialize_database()
ensure_default_admin()

if __name__ == "__main__":
    app.run(debug=True)
