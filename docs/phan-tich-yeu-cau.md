# Phân tích yêu cầu hệ thống

## 1. Mục tiêu

He_Thong_Tim_Viec kết nối ứng viên và nhà tuyển dụng, lưu trữ dữ liệu tuyển dụng có cấu trúc, sau đó dùng AI để phân tích CV và tính Matching Score giữa hồ sơ ứng viên với tin tuyển dụng. Dữ liệu giao dịch được chuẩn hóa để phục vụ dashboard BI.

## 2. Tác nhân

| Tác nhân | Mục tiêu chính |
|---|---|
| Ứng viên | Đăng ký, quản lý hồ sơ/CV, khai báo kỹ năng, tìm việc và ứng tuyển |
| Nhà tuyển dụng | Quản lý thông tin công ty, đăng tin, khai báo kỹ năng yêu cầu, xem và cập nhật hồ sơ ứng tuyển |
| Quản trị viên | Quản lý tài khoản, kiểm duyệt nội dung và theo dõi hoạt động hệ thống |
| Dịch vụ AI | Trích xuất kỹ năng từ CV/JD và tính điểm tương thích |
| Dịch vụ BI | Tổng hợp dữ liệu kỹ năng, lương và phễu tuyển dụng |

## 3. Chức năng chính

### Ứng viên

1. Đăng ký/đăng nhập và cập nhật thông tin cá nhân.
2. Tải CV, cập nhật tóm tắt nghề nghiệp và địa điểm.
3. Quản lý danh sách kỹ năng, mức độ thành thạo và số năm kinh nghiệm.
4. Tìm kiếm/lọc tin tuyển dụng theo kỹ năng, địa điểm, loại hình và mức lương.
5. Ứng tuyển một lần cho mỗi tin; theo dõi trạng thái hồ sơ.

### Nhà tuyển dụng

1. Quản lý hồ sơ công ty.
2. Tạo, sửa, đóng và lưu trữ tin tuyển dụng.
3. Khai báo kỹ năng bắt buộc/tùy chọn và số năm kinh nghiệm tối thiểu.
4. Xem hồ sơ ứng viên, Matching Score và cập nhật trạng thái tuyển dụng.

### AI và BI (giai đoạn sau)

1. Trích xuất kỹ năng chuẩn hóa từ CV và mô tả công việc.
2. Tính điểm theo kỹ năng, kinh nghiệm và các tiêu chí của JD; lưu kết quả tại hồ sơ ứng tuyển.
3. Cung cấp chỉ số ứng viên theo kỹ năng, phân bố lương, số lượng hồ sơ theo trạng thái và tỷ lệ chuyển đổi.

## 4. Yêu cầu phi chức năng

- **Bảo mật:** mật khẩu chỉ lưu dưới dạng hash; phân quyền theo vai trò; CV không public mặc định.
- **Toàn vẹn:** email duy nhất; không cho phép ứng viên ứng tuyển trùng một tin; khóa ngoại và trạng thái dùng giá trị hữu hạn.
- **Hiệu năng:** lập chỉ mục email, tên kỹ năng, tiêu đề tin và trạng thái tin để hỗ trợ tìm kiếm/lọc.
- **Mở rộng:** có thể chuyển SQLite sang PostgreSQL bằng `DATABASE_URL`; dữ liệu nghiệp vụ tách khỏi dữ liệu phân tích.
- **Truy vết:** mọi bản ghi nghiệp vụ chính có `created_at` và `updated_at`.
- **Khả dụng:** API có endpoint health check để kiểm tra dịch vụ.

## 5. Quy tắc nghiệp vụ cốt lõi

1. Một tài khoản có đúng một vai trò chính và một hồ sơ ứng viên hoặc nhà tuyển dụng tương ứng.
2. Chỉ nhà tuyển dụng sở hữu tin mới được sửa hoặc cập nhật trạng thái tin.
3. Chỉ tin ở trạng thái `open` mới nhận hồ sơ mới.
4. Một ứng viên không thể tạo nhiều hồ sơ cho cùng một tin.
5. `matching_score` là dữ liệu có thể được AI cập nhật; giai đoạn khởi tạo cho phép để trống.
6. Kỹ năng là danh mục dùng chung, được liên kết nhiều-nhiều với ứng viên và tin tuyển dụng.

