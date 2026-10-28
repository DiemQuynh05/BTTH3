# Smart Recruitment

Ứng dụng Django tìm việc thông minh dành cho sinh viên và người mới đi làm.
Bản triển khai hiện tại dùng Django Templates, Bootstrap 5, SQLite và Django
ORM; có thể chuyển sang PostgreSQL bằng `DATABASE_URL`.

## Chạy nhanh

```powershell
cd C:\Hoctap\HTKDTM\BTTH3\SmartRecruitment
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data
python manage.py seed_demo_data
python manage.py createsuperuser
python manage.py runserver
```

## PostgreSQL local

PostgreSQL 18 local của môi trường này chạy ở cổng `5433`, database của
Smart Recruitment là `smart_recruitment`. Cấu hình `DATABASE_URL` đã được lưu
ở cấp user Windows:

```powershell
$env:DATABASE_URL="postgresql://postgres@127.0.0.1:5433/smart_recruitment"
```

Nếu mở một terminal mới, chỉ cần kích hoạt lại virtual environment rồi chạy:

```powershell
cd C:\Hoctap\HTKDTM\BTTH3\SmartRecruitment
.\.venv\Scripts\Activate.ps1
python manage.py check
python manage.py runserver
```

Để kiểm tra Django đang dùng PostgreSQL:

```powershell
python manage.py shell -c "from django.conf import settings; print(settings.DATABASES['default']['ENGINE']); print(settings.DATABASES['default']['NAME'])"
```

Kết quả mong đợi:

```text
django.db.backends.postgresql
smart_recruitment
```

Nếu triển khai trên máy khác, thay URL bằng username, mật khẩu, host và port
PostgreSQL tương ứng. Không commit mật khẩu thật vào repository.

Mở `http://127.0.0.1:8000/`. Tài khoản được tạo bởi `seed_data` chỉ là dữ liệu
minh họa và được đặt mật khẩu không sử dụng được; hãy đăng ký tài khoản mới
hoặc tạo superuser để kiểm thử.

`seed_data` tạo dữ liệu mẫu tiếng Việt gồm 3 nhà tuyển dụng, 15 ứng viên, 30
tin tuyển dụng, 20 kỹ năng, CV PDF mẫu và 20 hồ sơ ứng tuyển. Lệnh có thể chạy
lặp lại; dữ liệu mẫu được nhận diện bằng username/email và khóa nghiệp vụ, nên
không nhân đôi bản ghi hoặc xóa dữ liệu hiện có.

## Tài khoản demo phát triển

Các thông tin dưới đây chỉ dùng cho môi trường local/demo, không sử dụng trong
production:

| Vai trò | Username | Email | Mật khẩu | Trang đăng nhập |
|---|---|---|---|---|
| Quản trị viên | `demo_admin` | `demo_admin@local.test` | `DemoAdmin123!` | `/admin/` |
| Ứng viên | `demo_candidate` | `demo_candidate@local.test` | `DemoCandidate123!` | `/accounts/login/` |
| Nhà tuyển dụng | `demo_employer` | `demo_employer@local.test` | `DemoEmployer123!` | `/accounts/login/` |

Để tạo ba tài khoản demo sau khi chạy migration, sử dụng PowerShell:

```powershell
python manage.py shell -c "from accounts.models import User; admin,_=User.objects.get_or_create(username='demo_admin', defaults={'email':'demo_admin@local.test','role':User.Role.ADMIN,'is_staff':True,'is_superuser':True}); admin.role=User.Role.ADMIN; admin.is_staff=True; admin.is_superuser=True; admin.email='demo_admin@local.test'; admin.set_password('DemoAdmin123!'); admin.save(); candidate,_=User.objects.get_or_create(username='demo_candidate', defaults={'email':'demo_candidate@local.test','role':User.Role.CANDIDATE}); candidate.role=User.Role.CANDIDATE; candidate.email='demo_candidate@local.test'; candidate.set_password('DemoCandidate123!'); candidate.save(); employer,_=User.objects.get_or_create(username='demo_employer', defaults={'email':'demo_employer@local.test','role':User.Role.EMPLOYER}); employer.role=User.Role.EMPLOYER; employer.email='demo_employer@local.test'; employer.set_password('DemoEmployer123!'); employer.save(); print('Demo accounts created or updated')"
```

Tài khoản ứng viên và nhà tuyển dụng có thể đăng nhập qua giao diện. Hồ sơ
tương ứng sẽ được tạo tự động khi đăng ký qua `/accounts/register/`; nếu tạo
trực tiếp bằng lệnh trên, có thể tạo profile từ Django shell:

```powershell
python manage.py shell -c "from accounts.models import User; from candidates.models import CandidateProfile; from employers.models import EmployerProfile; c=User.objects.get(username='demo_candidate'); CandidateProfile.objects.get_or_create(user=c); e=User.objects.get(username='demo_employer'); EmployerProfile.objects.get_or_create(user=e, defaults={'company_name':'Demo Recruitment Company'})"
```

## URL chính

- `/`: Trang chủ và tìm kiếm nhanh
- `/jobs/`: tìm kiếm, lọc và phân trang
- `/dashboard/`: BI Dashboard tổng hợp trực tiếp từ database
- `/accounts/register/`, `/accounts/login/`: xác thực
- `/candidates/profile/`: hồ sơ, CV ứng viên
- `/employers/profile/`, `/employers/jobs/`: hồ sơ và quản lý tin
- `/applications/`: danh sách hồ sơ đã ứng tuyển
- `/admin/`: quản trị dữ liệu

## Kiểm thử

```powershell
python manage.py check
python manage.py test
pytest
```

Các chức năng AI Matching và BI nâng cao chưa kết nối API, hiện có phần giới
thiệu giao diện để mở rộng về sau.

`seed_demo_data` tạo thêm 100 ứng viên, 20 nhà tuyển dụng, 50 tin tuyển dụng,
100 CV PDF mẫu, dữ liệu kỹ năng và 200 hồ sơ ứng tuyển. Điểm tương thích hiện
được tính bằng thuật toán **Rule-based Matching** minh bạch, không phải mô hình
Machine Learning và không gọi API AI bên ngoài. Command có thể chạy lặp lại mà
không nhân đôi dữ liệu demo.
