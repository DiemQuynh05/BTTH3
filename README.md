# Hệ thống tìm việc thông minh

Nền tảng tìm việc tích hợp dữ liệu ứng viên, CV, kỹ năng, tin tuyển dụng và
hồ sơ ứng tuyển. Cơ sở dữ liệu PostgreSQL cung cấp dữ liệu cho các chức năng
matching AI và báo cáo BI.

## 1. Công nghệ

- Python 3.11 trở lên
- Django 5.1
- PostgreSQL 18
- Psycopg 3
- SQLAlchemy và Alembic cho lớp mô hình/migration hiện có
- Pytest

Ứng dụng web hiện chạy bằng Django. Bộ SQL PostgreSQL là nguồn triển khai
schema, dữ liệu mẫu, View AI/BI và truy vấn kiểm tra chất lượng dữ liệu.

## 2. Cấu trúc hệ thống

```text
BTTH3/
├── manage.py                    # Điểm vào Django CLI
├── config/                      # Cấu hình project Django
│   ├── settings.py              # Cấu hình app, database, timezone
│   ├── urls.py                  # URL gốc và Django Admin
│   ├── asgi.py                  # Điểm vào ASGI
│   └── wsgi.py                  # Điểm vào WSGI
├── django_app/                  # Django app nền tảng
│   ├── apps.py
│   ├── urls.py                  # Endpoint /health/
│   └── views.py
├── app/                         # SQLAlchemy models và kết nối hiện có
│   ├── db/
│   ├── models/
│   └── config.py
├── postgresql/                  # Bộ triển khai database PostgreSQL
│   ├── 001_schema.sql           # Bảng, khóa, ràng buộc, index, trigger
│   ├── 002_seed.sql             # Dữ liệu mẫu an toàn
│   ├── 003_views.sql            # View phục vụ AI và BI
│   └── 004_data_quality.sql     # Kiểm tra dữ liệu và đối chiếu
├── scripts/
│   └── generate_demo_data.py    # Sinh dữ liệu giả theo quy mô
├── migrations/                  # Alembic migration của lớp SQLAlchemy
├── docs/                        # Tài liệu phân tích và thiết kế
├── tests/                       # Kiểm thử tự động
├── requirements.txt             # Dependency Python
├── .env.example                # Mẫu biến môi trường
└── .gitignore
```

## 3. Checklist cơ sở dữ liệu TV1

| STT | Nội dung | Thành phần |
|---|---|---|
| 1 | Tạo database và bảng nghiệp vụ | `postgresql/001_schema.sql` |
| 2 | Khóa chính, khóa ngoại và quan hệ | `PRIMARY KEY`, `FOREIGN KEY`, `UNIQUE`, `CHECK` |
| 3 | Dữ liệu mẫu | `postgresql/002_seed.sql` |
| 4 | Làm sạch và kiểm tra dữ liệu | `postgresql/004_data_quality.sql` |
| 5 | Dữ liệu cho AI matching | View `ai_candidate_job_skill_match` |
| 6 | Dataset cho BI | View `bi_application_kpi_daily`, `bi_job_funnel` |
| 7 | Kiểm thử và đối chiếu | Truy vấn trong `004_data_quality.sql` và Pytest |

Dữ liệu trong repository chỉ là dữ liệu mẫu hoặc dữ liệu giả phục vụ phát
triển. Không sử dụng các giá trị này cho môi trường production.

## 4. Chuẩn bị môi trường Python

Từ thư mục gốc repository:

```powershell
cd C:\Hoctap\HTKDTM\BTTH3\BTTH3
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Nếu PowerShell chặn chạy script trong phiên hiện tại:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

## 5. Triển khai PostgreSQL local

### 5.1. Tạo database

Đảm bảo PostgreSQL đang chạy, sau đó tạo database:

```powershell
createdb -U postgres -p 5432 he_thong_tim_viec
```

Nếu PostgreSQL chạy cổng khác, thay `5432` bằng cổng tương ứng. Máy phát triển
ban đầu của dự án sử dụng cổng `5433`.

### 5.2. Chạy schema và dữ liệu

Chạy đúng thứ tự:

```powershell
psql -U postgres -p 5432 -d he_thong_tim_viec -f postgresql/001_schema.sql
psql -U postgres -p 5432 -d he_thong_tim_viec -f postgresql/002_seed.sql
psql -U postgres -p 5432 -d he_thong_tim_viec -f postgresql/003_views.sql
psql -U postgres -p 5432 -d he_thong_tim_viec -f postgresql/004_data_quality.sql
```

Các truy vấn lỗi trong `004_data_quality.sql` phải trả về `0 rows`. Truy vấn
cuối cùng dùng để đối chiếu số lượng bản ghi.

### 5.3. Cấu hình kết nối

Tạo file `.env` từ `.env.example` và điền thông tin local:

```env
DJANGO_SECRET_KEY=change-this-for-local-development
DEBUG=true
ALLOWED_HOSTS=127.0.0.1,localhost
DATABASE_URL=postgresql+psycopg://postgres:MAT_KHAU@localhost:5432/he_thong_tim_viec
```

Không commit file `.env` hoặc mật khẩu lên GitHub. Mỗi thành viên dùng database
local và file `.env` riêng.

## 6. Chạy ứng dụng Django

Kiểm tra cấu hình:

```powershell
python manage.py check
```

Khởi động server phát triển:

```powershell
python manage.py runserver
```

Các địa chỉ chính:

- Health check: <http://127.0.0.1:8000/health/>
- Django Admin: <http://127.0.0.1:8000/admin/>

Tạo tài khoản quản trị local nếu cần:

```powershell
python manage.py createsuperuser
```

## 7. Sinh dữ liệu giả

Script không sử dụng dữ liệu người thật và chỉ thêm bản ghi mới:

```powershell
python scripts/generate_demo_data.py
```

Mặc định tạo:

- 100 ứng viên
- 20 nhà tuyển dụng
- 50 công việc
- 300 hồ sơ ứng tuyển

Điều chỉnh quy mô:

```powershell
python scripts/generate_demo_data.py `
  --applicants 1000 `
  --employers 100 `
  --jobs 500 `
  --applications 5000 `
  --prefix loadtest
```

Có thể đặt kết nối trực tiếp cho phiên PowerShell:

```powershell
$env:DATABASE_URL = "postgresql://postgres:MAT_KHAU@localhost:5432/he_thong_tim_viec"
python scripts/generate_demo_data.py
```

Mật khẩu của user demo là giá trị giả, không dùng cho xác thực thật.

## 8. Kiểm thử

Kiểm tra Django:

```powershell
python manage.py check
```

Chạy test:

```powershell
pytest
```

Kiểm tra chất lượng dữ liệu PostgreSQL:

```powershell
psql -U postgres -p 5432 -d he_thong_tim_viec `
  -f postgresql/004_data_quality.sql
```

## 9. Quy trình làm việc nhóm

Các thành viên làm việc trên nhánh riêng:

```powershell
git clone https://github.com/DiemQuynh05/BTTH3.git
cd BTTH3
git switch quynh
```

Các nhánh hiện có:

- `main`: mã đã được tích hợp và kiểm tra.
- `quynh`: nhánh của Quỳnh.
- `lananh`: nhánh của Lan Anh.
- `quan`: nhánh của Quân.
- `duc`: nhánh của Đức.

Trước khi làm việc:

```powershell
git switch ten-nhanh
git pull origin main
```

Sau khi hoàn thành:

```powershell
git add .
git commit -m "Mo ta thay doi"
git push origin ten-nhanh
```

Tạo Pull Request từ nhánh thành viên vào `main`. Không commit trực tiếp mật
khẩu, `.env`, database local, file backup PostgreSQL, `.venv` hoặc dữ liệu
ứng viên thật.
