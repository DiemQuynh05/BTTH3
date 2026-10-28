# Thiết kế cơ sở dữ liệu

## Mô hình quan hệ

- `users` 1-1 `applicants` hoặc `employers`.
- `employers` 1-n `job_postings`.
- `applicants` n-n `skills` qua `applicant_skills`.
- `job_postings` n-n `skills` qua `job_skills`.
- `applicants` n-n `job_postings` qua `applications`.

## Bảng và mục đích

| Bảng | Mục đích |
|---|---|
| `users` | Danh tính đăng nhập, vai trò và trạng thái tài khoản |
| `applicants` | Hồ sơ nghề nghiệp của ứng viên |
| `employers` | Thông tin doanh nghiệp/nhà tuyển dụng |
| `job_postings` | Tin tuyển dụng, lương, địa điểm và trạng thái |
| `skills` | Danh mục kỹ năng chuẩn hóa |
| `applicant_skills` | Kỹ năng, mức thành thạo và kinh nghiệm của ứng viên |
| `job_skills` | Kỹ năng yêu cầu của tin và số năm tối thiểu |
| `applications` | Hồ sơ ứng tuyển, trạng thái và Matching Score |

## Thiết kế cho AI/BI

- `applicant_skills` và `job_skills` là dữ liệu đầu vào chính cho mô hình matching.
- `applications.matching_score` lưu kết quả để sắp xếp ứng viên và đo hiệu quả gợi ý.
- Các cột trạng thái, thời gian tạo/cập nhật và mức lương hỗ trợ xây dựng fact/dimension cho BI ở giai đoạn sau.
- Không lưu dữ liệu dẫn xuất AI trong bảng danh mục; kết quả có thể được cập nhật hoặc tái tính toán.

Migration SQL khởi tạo nằm tại [`migrations/001_initial_schema.sql`](../migrations/001_initial_schema.sql).

## Triển khai PostgreSQL và dữ liệu phục vụ TV2/TV3

Bộ script PostgreSQL hoàn chỉnh nằm trong thư mục [`postgresql/`](../postgresql/):

- `001_schema.sql`: bảng, khóa, ràng buộc, index và trigger cập nhật thời gian.
- `002_seed.sql`: dữ liệu mẫu có thể chạy lặp lại.
- `003_views.sql`: View `ai_candidate_job_skill_match` cho TV2 và hai View KPI cho TV3.
- `004_data_quality.sql`: truy vấn phát hiện trùng lặp, thiếu dữ liệu, sai miền giá trị,
  bản ghi mồ côi và đối chiếu số lượng.

Schema PostgreSQL dùng `IDENTITY`, `TIMESTAMPTZ`, `CHECK`, `UNIQUE` và khóa ngoại
`ON DELETE CASCADE`; không dùng cú pháp SQLite.
