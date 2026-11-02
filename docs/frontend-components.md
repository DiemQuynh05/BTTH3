# Tài liệu Thành phần Giao diện Frontend (Frontend Components)

> **Dự án:** Smart Recruitment (Checklist 4)  
> **Công nghệ:** Django Templates, Bootstrap 5.3.3, Chart.js, HTML5/CSS3/ES6

---

## 1. Tổng quan Kiến trúc Giao diện

Hệ thống giao diện được tổ chức theo chuẩn Django Templates kế thừa từ template nền `base.html`:

- `templates/base.html`: Khung sườn chính, Navbar điều hướng, Dark mode toggle, Toast notification container, Footer.
- `templates/jobs/`:
  - `home.html`: Trang chủ & Hero section.
  - `list.html`: Tìm kiếm việc làm, bộ lọc từ khóa/địa điểm/loại hình/kỹ năng (`A1.3`), phân trang giữ tham số (`A1.4`).
  - `detail.html`: Chi tiết việc làm, Preview điểm AI Matching & phân tích kỹ năng thiếu (`A2.1-A2.3`), Thông tin doanh nghiệp (`A2.4`).
  - `dashboard.html`: BI & Analytics Dashboard với 4 biểu đồ Chart.js và bộ lọc đa chiều (`C1.1-C1.5`).
  - `employer_list.html`: Không gian quản lý tin tuyển dụng của doanh nghiệp (`A4.1`).
  - `applicants.html`: Bảng xếp hạng ứng viên theo AI Matching, Rescore real-time, chuyển trạng thái AJAX (`A4.2-A4.4`).
- `templates/candidates/`:
  - `profile.html`: Hồ sơ ứng viên, kéo thả upload CV (drag & drop), parse trích xuất kỹ năng inline (`A3.2-A3.4`).
- `templates/applications/`:
  - `list.html`: Danh sách việc làm đã ứng tuyển kèm Stepper / Timeline tiến trình xét duyệt trực quan (`A3.5`).

---

## 2. Các Thành phần Tương tác Cốt lõi

### 2.1. Dark Mode Theme Switcher (`A5.3`)
- **Cơ chế:** Dùng chuẩn `data-bs-theme="dark"` của Bootstrap 5.3 trên thẻ `<html>`.
- **Chống chớp sáng (FOUC):** Script đồng bộ tức thì trong `<head>` của `base.html` đọc trạng thái từ `localStorage.getItem("theme")` hoặc media query `prefers-color-scheme`.
- **Điều khiển:** Nút toggle `id="theme-toggle"` trên thanh Navbar; sự kiện xử lý trong `static/js/main.js`.

### 2.2. Bộ lọc Đa chiều & Phân trang (`A1.3`, `A1.4`)
- **Tập hợp bộ lọc:** Từ khóa (`q`), Địa điểm (`location`), Loại hình công việc (`job_type`), và Kỹ năng nổi bật (`skill`).
- **Giữ tham số phân trang:** Mọi liên kết trang đều bảo toàn querystring hiện tại thông qua template interpolation, tránh mất trạng thái lọc khi người dùng bấm chuyển trang.

### 2.3. Hộp thông tin Doanh nghiệp (`A2.4`)
- Nằm trong `templates/jobs/detail.html`.
- Hiển thị logo/avatar đại diện, tên công ty, ngành nghề hoạt động (`industry`), trụ sở (`address`), website liên kết và mô tả ngắn trích xuất từ `EmployerProfile`.

### 2.4. Timeline Hồ sơ Ứng tuyển (`A3.5`)
- CSS Stepper nằm trong `templates/applications/list.html` và `static/css/style.css`.
- 4 bước tiến trình:
  1. `Đã nộp đơn` (Status: `APPLIED`)
  2. `Xem xét hồ sơ` (Status: `REVIEWING`)
  3. `Phỏng vấn` (Status: `INTERVIEW`)
  4. `Trúng tuyển` (Status: `ACCEPTED`) hoặc `Chưa phù hợp` (Status: `REJECTED`)
- Màu sắc trực quan: Xanh lá (Hoàn thành), Xanh dương (Đang xử lý), Đỏ (Từ chối).

### 2.5. Bộ lọc BI Dashboard theo Thời gian & Ngành (`C1.5`)
- Tích hợp tại `templates/jobs/dashboard.html`.
- Các tiêu chí:
  - Khoảng thời gian: 7 ngày, 30 ngày (mặc định), 90 ngày (quý), 1 năm, hoặc toàn thời gian.
  - Loại hình công việc (`job_type`).
  - Ngành nghề công ty (`industry`).
- Gọi AJAX bất đồng bộ đến 5 API endpoint BI (`/api/bi/...`), tự động render lại toàn bộ 4 biểu đồ Chart.js mà không reload trang.

### 2.6. Drag & Drop CV Dropzone & Inline Parse Preview (`A3.2-A3.4`)
- Khu vực thả file CV (PDF / DOCX) tại `templates/candidates/profile.html`.
- Gọi AJAX tới `POST /api/cv/parse/`, tự động hiển thị kỹ năng nhận diện, năm kinh nghiệm và học vấn ngay dưới giao diện.

---

## 3. Quản lý Thư viện JavaScript & CSS

- `static/css/style.css`: Bổ sung toàn bộ style cho:
  - Stepper timeline (`.timeline-stepper`, `.timeline-icon`, `.timeline-step`).
  - Dark mode variables (`[data-bs-theme="dark"]`).
  - Score badge phân cấp (`.score-badge.high`, `.medium`, `.low`).
  - Toast notification popup (`.toast-notification`).
- `static/js/main.js`:
  - `window.AppUtils.showToast(message, type)`
  - `window.AppUtils.fetchJson(url, options)`
  - `initTheme()` cho Dark/Light mode toggle.
