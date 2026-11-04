from __future__ import annotations

import sqlite3
from typing import Any

from app.database.connection import get_connection


class SchoolRepository:
    """Tập trung các truy vấn dữ liệu của ứng dụng."""

    @staticmethod
    def dashboard() -> dict[str, Any]:
        with get_connection() as db:
            totals = db.execute(
                """SELECT (SELECT COUNT(*) FROM students) AS students,
                          (SELECT COUNT(*) FROM classes) AS classes,
                          (SELECT COUNT(*) FROM grades) AS grades,
                          (SELECT COUNT(*) FROM students WHERE gender = 'Nam') AS male,
                          (SELECT COUNT(*) FROM students WHERE gender = 'Nữ') AS female"""
            ).fetchone()
            classes = db.execute(
                """SELECT c.name, c.code, c.major, c.homeroom_teacher,
                          COUNT(s.id) AS student_count
                   FROM classes c LEFT JOIN students s ON s.class_id = c.id
                   GROUP BY c.id ORDER BY c.name"""
            ).fetchall()
            recent = db.execute(
                """SELECT s.code, s.full_name, s.email, COALESCE(c.name, 'Chưa xếp lớp') AS class_name
                   FROM students s LEFT JOIN classes c ON c.id = s.class_id
                   ORDER BY s.id DESC LIMIT 6"""
            ).fetchall()
            recent_grades = db.execute(
                """SELECT s.code, s.full_name, g.subject, g.score, g.semester
                   FROM grades g JOIN students s ON s.id=g.student_id
                   ORDER BY g.id DESC LIMIT 5"""
            ).fetchall()
            unassigned = db.execute("SELECT COUNT(*) FROM students WHERE class_id IS NULL").fetchone()[0]
            return {"totals": dict(totals), "classes": [dict(r) for r in classes],
                    "recent": [dict(r) for r in recent],
                    "recent_grades": [dict(r) for r in recent_grades], "unassigned": unassigned}

    @staticmethod
    def report_data() -> dict[str, Any]:
        with get_connection() as db:
            total = db.execute("SELECT COUNT(*) FROM students").fetchone()[0]
            grade_stats = db.execute(
                """SELECT COUNT(*) AS count, AVG(score) AS average,
                          SUM(CASE WHEN score >= 8 THEN 1 ELSE 0 END) AS excellent,
                          SUM(CASE WHEN score >= 6.5 AND score < 8 THEN 1 ELSE 0 END) AS good,
                          SUM(CASE WHEN score >= 5 AND score < 6.5 THEN 1 ELSE 0 END) AS average_count,
                          SUM(CASE WHEN score < 5 THEN 1 ELSE 0 END) AS weak
                   FROM grades"""
            ).fetchone()
            classes = db.execute(
                """SELECT c.id, c.code, c.name, c.major, c.homeroom_teacher, COUNT(s.id) AS student_count
                   FROM classes c LEFT JOIN students s ON s.class_id=c.id
                   GROUP BY c.id ORDER BY student_count DESC, c.name"""
            ).fetchall()
            gender = db.execute("SELECT gender, COUNT(*) AS count FROM students GROUP BY gender").fetchall()
            unassigned = db.execute("SELECT COUNT(*) FROM students WHERE class_id IS NULL").fetchone()[0]
            return {"totals": {"students": total, "unassigned": unassigned},
                    "grades": dict(grade_stats), "classes": [dict(r) for r in classes],
                    "gender": [dict(r) for r in gender]}

    @staticmethod
    def get_settings() -> dict[str, str]:
        defaults = {"institution_name": "Student Management", "academic_year": "2026–2027",
                    "default_semester": "Học kỳ 1", "items_per_page": "20", "allow_csv_export": "1",
                    "theme": "light", "accent_color": "blue", "font_scale": "normal",
                    "compact_tables": "0", "show_dashboard_banner": "1"}
        with get_connection() as db:
            rows = db.execute("SELECT setting_key, setting_value FROM app_settings").fetchall()
            defaults.update({r["setting_key"]: r["setting_value"] for r in rows})
        return defaults

    @staticmethod
    def save_settings(values: dict[str, str]) -> None:
        with get_connection() as db:
            db.executemany("""INSERT INTO app_settings(setting_key,setting_value) VALUES(?,?)
                ON CONFLICT(setting_key) DO UPDATE SET setting_value=excluded.setting_value""", values.items())

    @staticmethod
    def update_account(user_id: int, display_name: str, new_password_hash: str | None = None) -> None:
        with get_connection() as db:
            if new_password_hash:
                db.execute("UPDATE users SET display_name=?, password_hash=? WHERE id=?",
                           (display_name, new_password_hash, user_id))
            else:
                db.execute("UPDATE users SET display_name=? WHERE id=?", (display_name, user_id))

    @staticmethod
    def list_subjects(search: str = "") -> list[dict[str, Any]]:
        sql = """SELECT sub.*, COUNT(DISTINCT g.id) AS grade_count
                 FROM subjects sub LEFT JOIN grades g ON g.subject=sub.name WHERE 1=1"""
        params: list[Any] = []
        if search.strip():
            sql += " AND (sub.code LIKE ? OR sub.name LIKE ? OR sub.major LIKE ?)"
            term = f"%{search.strip()}%"
            params.extend((term, term, term))
        sql += " GROUP BY sub.id ORDER BY sub.name"
        with get_connection() as db:
            return [dict(r) for r in db.execute(sql, params).fetchall()]

    @staticmethod
    def save_subject(data: dict[str, Any], record_id: int | None = None) -> None:
        with get_connection() as db:
            if record_id:
                db.execute("UPDATE subjects SET code=?,name=?,credits=?,major=? WHERE id=?",
                           (data["code"], data["name"], data["credits"], data["major"], record_id))
            else:
                db.execute("INSERT INTO subjects(code,name,credits,major) VALUES(?,?,?,?)",
                           (data["code"], data["name"], data["credits"], data["major"]))

    @staticmethod
    def delete_subject(record_id: int) -> None:
        with get_connection() as db:
            db.execute("DELETE FROM subjects WHERE id=?", (record_id,))

    @staticmethod
    def attendance_data(search: str = "", status: str = "", subject_id: int | None = None,
                        class_id: int | None = None) -> dict[str, Any]:
        sql = """SELECT a.*, s.code, s.full_name, COALESCE(sub.name,'Chưa gắn môn') AS subject_name
                 FROM attendance a JOIN students s ON s.id=a.student_id
                 LEFT JOIN subjects sub ON sub.id=a.subject_id WHERE 1=1"""
        params: list[Any] = []
        if search.strip():
            sql += " AND (s.code LIKE ? OR s.full_name LIKE ?)"
            term = f"%{search.strip()}%"
            params.extend((term, term))
        if status:
            sql += " AND a.status=?"
            params.append(status)
        if subject_id:
            sql += " AND a.subject_id=?"
            params.append(subject_id)
        if class_id:
            sql += " AND s.class_id=?"
            params.append(class_id)
        sql += " ORDER BY a.attendance_date DESC, s.full_name"
        with get_connection() as db:
            rows = [dict(r) for r in db.execute(sql, params).fetchall()]
            counts = {"total": len(rows), "present": sum(r["status"] == "Có mặt" for r in rows),
                      "absent": sum(r["status"] == "Vắng" for r in rows),
                      "late": sum(r["status"] == "Muộn" for r in rows),
                      "excused": sum(r["status"] == "Có phép" for r in rows)}
            return {"rows": rows, "counts": counts}

    @staticmethod
    def attendance_roster(search: str = "", class_id: int | None = None, attendance_date: str = "",
                          subject_id: int | None = None) -> list[dict[str, Any]]:
        sql = """SELECT s.id,s.code,s.full_name,COALESCE(c.code,'—') AS class_code,
                    COALESCE(c.name,'Chưa xếp lớp') AS class_name,
                    a.id AS attendance_id,a.status AS attendance_status
                 FROM students s LEFT JOIN classes c ON c.id=s.class_id
                 LEFT JOIN attendance a ON a.student_id=s.id AND a.attendance_date=?
                    AND a.subject_id IS ? WHERE 1=1"""
        params: list[Any] = [attendance_date, subject_id]
        if search.strip():
            term = f"%{search.strip()}%"
            sql += " AND (s.code LIKE ? OR s.full_name LIKE ?)"
            params.extend((term, term))
        if class_id:
            sql += " AND s.class_id=?"
            params.append(class_id)
        sql += " ORDER BY c.name,s.full_name"
        with get_connection() as db:
            return [dict(row) for row in db.execute(sql, params).fetchall()]

    @staticmethod
    def quick_save_attendance(student_id: int, subject_id: int | None, attendance_date: str, status: str) -> None:
        with get_connection() as db:
            existing = db.execute("""SELECT id FROM attendance
                WHERE student_id=? AND subject_id IS ? AND attendance_date=?""",
                (student_id, subject_id, attendance_date)).fetchone()
            if existing:
                db.execute("UPDATE attendance SET status=? WHERE id=?", (status, existing["id"]))
            else:
                db.execute("""INSERT INTO attendance(student_id,subject_id,attendance_date,status,note)
                    VALUES(?,?,?,?,?)""", (student_id, subject_id, attendance_date, status, ""))

    @staticmethod
    def save_attendance(data: dict[str, Any], record_id: int | None = None) -> None:
        with get_connection() as db:
            if record_id:
                db.execute("""UPDATE attendance SET student_id=?,subject_id=?,attendance_date=?,status=?,note=?,section_id=NULL WHERE id=?""",
                           (data["student_id"], data["subject_id"], data["attendance_date"], data["status"], data["note"],record_id))
            else:
                db.execute("""INSERT INTO attendance(student_id,subject_id,attendance_date,status,note) VALUES(?,?,?,?,?)""",
                           (data["student_id"], data["subject_id"], data["attendance_date"], data["status"], data["note"]))

    @staticmethod
    def delete_attendance(record_id: int) -> None:
        with get_connection() as db:
            db.execute("DELETE FROM attendance WHERE id=?", (record_id,))

    @staticmethod
    def list_classes() -> list[dict[str, Any]]:
        with get_connection() as db:
            rows = db.execute(
                """SELECT c.*, COUNT(s.id) AS student_count
                   FROM classes c LEFT JOIN students s ON s.class_id = c.id
                   GROUP BY c.id ORDER BY c.name"""
            ).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def class_detail(class_id: int) -> dict[str, Any] | None:
        with get_connection() as db:
            cls = db.execute("""SELECT c.*,COUNT(DISTINCT s.id) AS student_count,
                COUNT(DISTINCT g.id) AS grade_count,AVG(g.score) AS class_average
                FROM classes c LEFT JOIN students s ON s.class_id=c.id
                LEFT JOIN grades g ON g.student_id=s.id WHERE c.id=? GROUP BY c.id""", (class_id,)).fetchone()
            if not cls:
                return None
            students = db.execute("""SELECT s.*,COUNT(DISTINCT g.id) AS grade_count,AVG(g.score) AS average
                FROM students s LEFT JOIN grades g ON g.student_id=s.id
                WHERE s.class_id=? GROUP BY s.id ORDER BY s.full_name""", (class_id,)).fetchall()
            grades = db.execute("""SELECT s.code,s.full_name,g.subject,g.score
                FROM grades g JOIN students s ON s.id=g.student_id WHERE s.class_id=?
                ORDER BY g.id DESC""", (class_id,)).fetchall()
            attendance_rows = db.execute("""SELECT s.code,s.full_name,a.attendance_date,
                COALESCE(sub.name,'Chưa gắn môn') AS subject_name,a.status,a.note
                FROM attendance a JOIN students s ON s.id=a.student_id
                LEFT JOIN subjects sub ON sub.id=a.subject_id WHERE s.class_id=?
                ORDER BY a.attendance_date DESC,a.id DESC""", (class_id,)).fetchall()
            attendance = db.execute("""SELECT COUNT(*) AS total,
                SUM(CASE WHEN a.status='Có mặt' THEN 1 ELSE 0 END) AS present,
                SUM(CASE WHEN a.status='Vắng' THEN 1 ELSE 0 END) AS absent
                FROM attendance a JOIN students s ON s.id=a.student_id WHERE s.class_id=?""", (class_id,)).fetchone()
            return {"class": dict(cls), "students": [dict(r) for r in students],
                    "grades": [dict(r) for r in grades], "attendance_rows": [dict(r) for r in attendance_rows],
                    "attendance": dict(attendance)}

    @staticmethod
    def save_class(data: dict[str, Any], record_id: int | None = None) -> None:
        with get_connection() as db:
            if record_id:
                db.execute("UPDATE classes SET code=?, name=?, major=?, homeroom_teacher=? WHERE id=?",
                           (data["code"], data["name"], data["major"], data["homeroom_teacher"], record_id))
            else:
                db.execute("INSERT INTO classes(code,name,major,homeroom_teacher) VALUES(?,?,?,?)",
                           (data["code"], data["name"], data["major"], data["homeroom_teacher"]))

    @staticmethod
    def delete_class(record_id: int) -> None:
        with get_connection() as db:
            db.execute("DELETE FROM classes WHERE id=?", (record_id,))

    @staticmethod
    def list_students(search: str = "", class_id: int | None = None, gender: str = "") -> list[dict[str, Any]]:
        sql = """SELECT s.*, COALESCE(c.name, 'Chưa xếp lớp') AS class_name,
                        COALESCE(c.code, '—') AS class_code,
                        (SELECT COUNT(*) FROM grades g WHERE g.student_id=s.id) AS grade_count,
                        (SELECT COUNT(*) FROM attendance a WHERE a.student_id=s.id) AS attendance_count
                 FROM students s LEFT JOIN classes c ON c.id=s.class_id WHERE 1=1"""
        params: list[Any] = []
        if search.strip():
            sql += " AND (s.code LIKE ? OR s.full_name LIKE ?)"
            params += [f"%{search.strip()}%", f"%{search.strip()}%"]
        if class_id:
            sql += " AND s.class_id=?"
            params.append(class_id)
        if gender:
            sql += " AND s.gender=?"
            params.append(gender)
        sql += " ORDER BY s.id DESC"
        with get_connection() as db:
            return [dict(r) for r in db.execute(sql, params).fetchall()]

    @staticmethod
    def save_student(data: dict[str, Any], record_id: int | None = None) -> None:
        with get_connection() as db:
            if data["class_id"] and not data["major"]:
                class_major = db.execute("SELECT major FROM classes WHERE id=?", (data["class_id"],)).fetchone()
                if class_major:
                    data["major"] = class_major["major"]
            fields = (data["code"], data["full_name"], data["birth_date"], data["gender"], data["address"],
                      data["phone"], data["email"], data["class_id"], data["major"])
            if record_id:
                db.execute("""UPDATE students SET code=?,full_name=?,birth_date=?,gender=?,address=?,phone=?,email=?,class_id=?,major=? WHERE id=?""",
                           (*fields, record_id))
            else:
                db.execute("""INSERT INTO students(code,full_name,birth_date,gender,address,phone,email,class_id,major) VALUES(?,?,?,?,?,?,?,?,?)""", fields)

    @staticmethod
    def delete_student(record_id: int) -> None:
        with get_connection() as db:
            db.execute("DELETE FROM students WHERE id=?", (record_id,))

    @staticmethod
    def list_grades(search: str = "", class_id: int | None = None,
                    subject_id: int | None = None) -> list[dict[str, Any]]:
        sql = """SELECT g.*, s.code, s.full_name, c.code AS class_code, c.name AS class_name FROM grades g
                 JOIN students s ON s.id=g.student_id LEFT JOIN classes c ON c.id=s.class_id WHERE 1=1"""
        params: list[Any] = []
        if search.strip():
            sql += " AND (s.code LIKE ? OR s.full_name LIKE ? OR g.subject LIKE ?)"
            term = f"%{search.strip()}%"
            params.extend((term, term, term))
        if class_id:
            sql += " AND s.class_id=?"
            params.append(class_id)
        if subject_id:
            sql += " AND g.subject=(SELECT name FROM subjects WHERE id=?)"
            params.append(subject_id)
        sql += " ORDER BY s.full_name, g.semester, g.subject"
        with get_connection() as db:
            rows = [dict(r) for r in db.execute(sql, params).fetchall()]
            for row in rows:
                row["average"] = db.execute("SELECT AVG(score) FROM grades WHERE student_id=?",
                                            (row["student_id"],)).fetchone()[0]
            return rows

    @staticmethod
    def grade_roster(class_id: int, subject_id: int, search: str = "") -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
        with get_connection() as db:
            subject = db.execute("SELECT id,code,name FROM subjects WHERE id=?", (subject_id,)).fetchone()
            if not subject:
                return None, []
            sql = """SELECT s.id,s.code,s.full_name,c.code AS class_code,c.name AS class_name,
                (SELECT g.id FROM grades g WHERE g.student_id=s.id AND g.subject=? ORDER BY g.id DESC LIMIT 1) AS grade_id,
                (SELECT g.score FROM grades g WHERE g.student_id=s.id AND g.subject=? ORDER BY g.id DESC LIMIT 1) AS score,
                (SELECT AVG(g.score) FROM grades g WHERE g.student_id=s.id) AS average
                FROM students s JOIN classes c ON c.id=s.class_id WHERE c.id=?"""
            params: list[Any] = [subject["name"], subject["name"], class_id]
            if search.strip():
                term = f"%{search.strip()}%"
                sql += " AND (s.code LIKE ? OR s.full_name LIKE ?)"
                params.extend((term, term))
            sql += " ORDER BY s.full_name"
            rows = [dict(row) for row in db.execute(sql, params).fetchall()]
            return dict(subject), rows

    @staticmethod
    def save_grade(data: dict[str, Any], record_id: int | None = None) -> None:
        with get_connection() as db:
            if not db.execute("SELECT 1 FROM students WHERE id=?", (data["student_id"],)).fetchone():
                raise ValueError("Không tìm thấy sinh viên để nhập điểm.")
            if not db.execute("SELECT 1 FROM subjects WHERE name=?", (data["subject"],)).fetchone():
                raise ValueError("Môn học không tồn tại. Hãy chọn môn trong danh sách môn học.")
            if record_id:
                db.execute("UPDATE grades SET student_id=?, subject=?, semester=?, score=?,section_id=NULL WHERE id=?",
                           (data["student_id"], data["subject"], data["semester"], data["score"],record_id))
            else:
                existing = db.execute("SELECT id FROM grades WHERE student_id=? AND subject=? ORDER BY id DESC LIMIT 1",
                                      (data["student_id"], data["subject"])).fetchone()
                if existing:
                    db.execute("UPDATE grades SET score=? WHERE id=?", (data["score"], existing["id"]))
                else:
                    db.execute("INSERT INTO grades(student_id,subject,semester,score) VALUES(?,?,?,?)",
                               (data["student_id"], data["subject"], data["semester"], data["score"]))

    @staticmethod
    def delete_grade(record_id: int) -> None:
        with get_connection() as db:
            db.execute("DELETE FROM grades WHERE id=?", (record_id,))

    @staticmethod
    def class_options() -> list[dict[str, Any]]:
        with get_connection() as db:
            return [dict(r) for r in db.execute("SELECT id,code,name FROM classes ORDER BY name").fetchall()]

    @staticmethod
    def student_options() -> list[dict[str, Any]]:
        with get_connection() as db:
            return [dict(r) for r in db.execute("SELECT id,code,full_name FROM students ORDER BY full_name").fetchall()]
