# He_Thong_Tim_Viec

Nền tảng tìm việc thông minh tích hợp AI và BI.

## Trạng thái checklist TV1

| STT | Nội dung | Trạng thái |
|---|---|---|
| 1 | Tạo CSDL và bảng nghiệp vụ | Hoàn thành: SQLite và bộ schema PostgreSQL |
| 2 | Khóa chính, khóa ngoại, quan hệ | Hoàn thành |
| 3 | Dữ liệu mẫu ứng viên, CV, việc, kỹ năng, hồ sơ | Hoàn thành trong `postgresql/002_seed.sql` |
| 4 | Làm sạch và kiểm tra dữ liệu | Hoàn thành trong `postgresql/004_data_quality.sql` |
| 5 | View/truy vấn phục vụ AI | Hoàn thành: `ai_candidate_job_skill_match` |
| 6 | View/truy vấn phục vụ BI | Hoàn thành: `bi_application_kpi_daily`, `bi_job_funnel` |
| 7 | Kiểm thử và đối chiếu | Có checklist truy vấn; cần chạy trên PostgreSQL thật để chốt biên bản |

Mô hình ORM và SQLite vẫn được giữ để chạy backend hiện tại. Bộ SQL PostgreSQL là
đường triển khai đầy đủ cho TV1.

## Yêu cầu môi trường

- Python 3.11 trở lên
- `venv`

## Khởi tạo và chạy backend

PowerShell:

```powershell
cd C:\Hoctap\HTKDTM\BTTH3\He_Thong_Tim_Viec
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

Mở tài liệu API tại <http://127.0.0.1:8000/docs>.

## Khởi tạo PostgreSQL

Tạo database trước (ví dụ `he_thong_tim_viec`), sau đó chạy theo đúng thứ tự:

```powershell
psql -h localhost -p 5433 -U postgres -d he_thong_tim_viec -f postgresql/001_schema.sql
psql -h localhost -p 5433 -U postgres -d he_thong_tim_viec -f postgresql/002_seed.sql
psql -h localhost -p 5433 -U postgres -d he_thong_tim_viec -f postgresql/003_views.sql
psql -h localhost -p 5433 -U postgres -d he_thong_tim_viec -f postgresql/004_data_quality.sql
```

`004_data_quality.sql` phải trả về 0 dòng ở các truy vấn lỗi; truy vấn cuối
dùng để đối chiếu số lượng bản ghi. Để backend dùng PostgreSQL, đặt
`DATABASE_URL=postgresql+psycopg://...` trong `.env`.

## Sinh dữ liệu giả

Script dùng dữ liệu tạo tự động, không chứa thông tin người thật. Mặc định tạo
100 ứng viên, 20 nhà tuyển dụng, 50 công việc và 300 hồ sơ ứng tuyển:

```powershell
$env:DATABASE_URL = "postgresql://postgres@localhost:5433/he_thong_tim_viec"
python scripts/generate_demo_data.py
```

Có thể điều chỉnh quy mô và dùng prefix riêng để chạy nhiều lần:

```powershell
python scripts/generate_demo_data.py --applicants 1000 --employers 100 --jobs 500 --applications 5000 --prefix loadtest
```

Script chỉ thêm bản ghi mới, không xóa dữ liệu hiện có. Mật khẩu trong các
user sinh ra là giá trị giả (`demo-only-hash`), không dùng cho đăng nhập thật.

## Kiểm thử

```powershell
pytest
```

## Cấu trúc

```text
He_Thong_Tim_Viec/
├── app/
│   ├── db/
│   ├── models/
│   ├── schemas/
│   └── main.py
├── docs/
│   ├── phan-tich-yeu-cau.md
│   └── thiet-ke-co-so-du-lieu.md
├── migrations/
│   └── 001_initial_schema.sql
├── postgresql/
│   ├── 001_schema.sql
│   ├── 002_seed.sql
│   ├── 003_views.sql
│   └── 004_data_quality.sql
├── tests/
├── .env.example
├── alembic.ini
└── requirements.txt
```
