# Student Management — Ứng dụng web quản lý sinh viên

Ứng dụng web viết bằng **Python + Flask**, lưu dữ liệu bằng **SQLite**. Giao diện tiếng Việt, nền trắng và dùng xanh dương/xanh lá/cam/tím làm màu nhấn cho nút, trạng thái và số liệu.

## Chức năng

- Dashboard với số sinh viên, lớp, đầu điểm, cơ cấu giới tính, lớp học và sinh viên mới.
- Quản lý sinh viên: thêm, sửa, xóa, tìm theo mã/tên, lọc theo lớp/giới tính, xuất CSV UTF-8.
- Quản lý lớp: thêm, sửa, xóa, theo dõi sĩ số và giáo viên chủ nhiệm.
- Quản lý điểm: thêm, sửa, xóa, tìm kiếm, tính điểm trung bình theo học kỳ và xếp loại.
- Quản lý môn học và điểm danh: thêm, sửa, xóa; lọc điểm danh theo trạng thái, môn và sinh viên.
- Nhập hàng loạt sinh viên, lớp, môn học, điểm và điểm danh từ Excel (.xlsx) hoặc CSV; có tệp mẫu và xem trước lỗi/trùng lặp.
- Thống kê sinh viên theo giới tính và sĩ số từng lớp.
- Đăng nhập, đăng xuất và bảo vệ các trang quản lý bằng phiên đăng nhập.
- Tùy chỉnh giao diện: chế độ sáng/tối, 5 màu nhấn, cỡ chữ, bảng gọn và banner tổng quan.
- Cài đặt tên hệ thống, năm học, học kỳ mặc định, số dòng mỗi trang, quyền xuất CSV, tên tài khoản và mật khẩu.
- Dashboard tập trung vào việc cần làm và cập nhật gần đây; trang báo cáo phân tích riêng cơ cấu giới tính, sĩ số lớp và phân loại điểm.

## Chạy trên Windows

Yêu cầu Python 3.10 trở lên. Mở PowerShell tại thư mục dự án và chạy:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

Mở trình duyệt tại [http://127.0.0.1:5000](http://127.0.0.1:5000). Nhấn `Ctrl+C` trong terminal để dừng máy chủ.

Tài khoản quản trị lần đầu: **admin** / **admin123**. Mật khẩu được băm trong SQLite; hãy thay đổi giá trị mặc định trước khi dùng trong môi trường nhiều người.

Tài khoản quản trị lần đầu: **admin** / **admin123**. Mật khẩu được băm trong SQLite; hãy thay đổi giá trị mặc định trước khi dùng trong môi trường nhiều người.

SQLite được lưu tại `data/student_management.db` và tự tạo khi khởi chạy ứng dụng.

## Nhập dữ liệu từ Excel / CSV

Mở phân hệ cần nhập (Sinh viên, Lớp, Môn học, Điểm hoặc Điểm danh), chọn **Nhập tệp**, tải mẫu `.xlsx`, điền dữ liệu và tải lên. Hệ thống xem trước tối đa 100 dòng, báo các dòng thiếu dữ liệu, mã trùng hoặc tham chiếu chưa có; chỉ dòng hợp lệ được nhập khi xác nhận. Có thể dùng tệp `.csv` UTF-8 với hàng tiêu đề theo mẫu. Mỗi lần tối đa 10.000 dòng và 8 MB.

Với điểm và điểm danh, cần nhập lớp/sinh viên/môn học tương ứng trước để các mã tham chiếu được nhận diện.

## Cấu trúc

```text
QLsinhVien/
├── app/
│   ├── database/          # Kết nối và schema SQLite
│   ├── repositories/      # Truy vấn, thao tác dữ liệu
│   ├── templates/         # Các trang HTML/Jinja
│   ├── static/            # CSS và JavaScript
│   └── web.py             # Flask routes
├── data/                  # Cơ sở dữ liệu cục bộ
├── requirements.txt
└── run.py                 # Điểm khởi chạy web server
```

## Mô hình dữ liệu

- `classes`: mã lớp, tên lớp, ngành, giáo viên chủ nhiệm.
- `students`: thông tin sinh viên và liên kết lớp; khi xóa lớp, sinh viên được giữ lại.
- `grades`: môn học, học kỳ, điểm từ 0 đến 10; khi xóa sinh viên, điểm liên quan được xóa.

Máy chủ mặc định chỉ lắng nghe trên `127.0.0.1` để chạy cục bộ.
