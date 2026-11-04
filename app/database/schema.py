from .connection import get_connection


def initialize_database() -> None:
    """Tạo các bảng cần thiết; an toàn khi chạy lại nhiều lần."""
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS classes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                major TEXT NOT NULL DEFAULT '',
                homeroom_teacher TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                full_name TEXT NOT NULL,
                birth_date TEXT NOT NULL DEFAULT '',
                gender TEXT NOT NULL DEFAULT '',
                address TEXT NOT NULL DEFAULT '',
                phone TEXT NOT NULL DEFAULT '',
                email TEXT NOT NULL DEFAULT '',
                class_id INTEGER,
                major TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS grades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                semester TEXT NOT NULL DEFAULT 'Học kỳ 1',
                score REAL NOT NULL CHECK(score >= 0 AND score <= 10),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(student_id, subject, semester),
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                display_name TEXT NOT NULL DEFAULT 'Quản trị viên',
                role TEXT NOT NULL DEFAULT 'admin',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS app_settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                credits INTEGER NOT NULL DEFAULT 3 CHECK(credits > 0 AND credits <= 12),
                major TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                subject_id INTEGER,
                attendance_date TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('Có mặt','Vắng','Muộn','Có phép')),
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(student_id, subject_id, attendance_date),
                FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE,
                FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS academic_terms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                academic_year TEXT NOT NULL,
                start_date TEXT NOT NULL DEFAULT '',
                end_date TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'Đang mở' CHECK(status IN ('Đang mở','Đã khóa')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS course_sections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                subject_id INTEGER NOT NULL,
                term_id INTEGER NOT NULL,
                instructor TEXT NOT NULL DEFAULT '',
                capacity INTEGER NOT NULL DEFAULT 40 CHECK(capacity > 0),
                status TEXT NOT NULL DEFAULT 'Đang mở' CHECK(status IN ('Đang mở','Đã khóa')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE RESTRICT,
                FOREIGN KEY(term_id) REFERENCES academic_terms(id) ON DELETE RESTRICT
            );

            CREATE TABLE IF NOT EXISTS enrollments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section_id INTEGER NOT NULL,
                student_id INTEGER NOT NULL,
                enrolled_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL DEFAULT 'Đang học' CHECK(status IN ('Đang học','Đã hủy')),
                UNIQUE(section_id, student_id),
                FOREIGN KEY(section_id) REFERENCES course_sections(id) ON DELETE CASCADE,
                FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS import_batches (
                id TEXT PRIMARY KEY,
                entity TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'preview',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS import_rows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id TEXT NOT NULL,
                row_number INTEGER NOT NULL,
                payload TEXT NOT NULL,
                error TEXT NOT NULL DEFAULT '',
                FOREIGN KEY(batch_id) REFERENCES import_batches(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS support_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'Lỗi chức năng',
                priority TEXT NOT NULL DEFAULT 'Trung bình' CHECK(priority IN ('Thấp','Trung bình','Cao','Khẩn cấp')),
                description TEXT NOT NULL,
                reporter_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'Mới tiếp nhận' CHECK(status IN ('Mới tiếp nhận','Đang xử lý','Chờ phản hồi','Đã giải quyết')),
                resolution_note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(reporter_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_students_name ON students(full_name);
            CREATE INDEX IF NOT EXISTS idx_students_class ON students(class_id);
            CREATE INDEX IF NOT EXISTS idx_grades_student ON grades(student_id);
            CREATE INDEX IF NOT EXISTS idx_enrollments_section ON enrollments(section_id);
            CREATE INDEX IF NOT EXISTS idx_enrollments_student ON enrollments(student_id);
            """
        )
        # Safe migrations for databases created before academic sections existed.
        grade_columns = {row["name"] for row in connection.execute("PRAGMA table_info(grades)")}
        if "section_id" not in grade_columns:
            connection.execute("ALTER TABLE grades ADD COLUMN section_id INTEGER REFERENCES course_sections(id) ON DELETE SET NULL")
        attendance_columns = {row["name"] for row in connection.execute("PRAGMA table_info(attendance)")}
        if "section_id" not in attendance_columns:
            connection.execute("ALTER TABLE attendance ADD COLUMN section_id INTEGER REFERENCES course_sections(id) ON DELETE SET NULL")
