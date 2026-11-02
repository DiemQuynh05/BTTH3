# Tài liệu API AI Matching & BI Dashboard (Checklist 4)

Tài liệu đặc tả các API endpoints được tích hợp phục vụ giao diện Frontend, bóc tách CV tự động, AI Matching và phân tích thị trường BI.

---

## 1. AI Matching & CV Parser APIs

### 1.1 Xem trước điểm tương thích (Match Preview)
- **URL:** `/api/match/preview/`
- **Method:** `GET` hoặc `POST`
- **Yêu cầu đăng nhập:** Có (Candidate hoặc Employer/Admin)
- **Tham số:**
  - `job_id` (bắt buộc): ID tin tuyển dụng
  - `candidate_id` (tùy chọn, chỉ dành cho Employer/Admin)
- **Response mẫu:**
```json
{
  "status": "success",
  "job_id": 1,
  "job_title": "Python Developer",
  "score": 85.0,
  "explanation": {
    "method": "ml",
    "matched_skills": ["Python", "SQL"],
    "missing_required_skills": [],
    "required_skills": "2/2",
    "top_factors": [
      {"label": "Kỹ năng bắt buộc", "impact": 25.5},
      {"label": "Độ trùng khớp kỹ năng", "impact": 18.2}
    ]
  }
}
```

---

### 1.2 Bóc tách thông tin CV (CV Parse)
- **URL:** `/api/cv/parse/`
- **Method:** `POST`
- **Content-Type:** `multipart/form-data` hoặc `application/x-www-form-urlencoded`
- **Tham số:**
  - `file`: File upload (.pdf, .docx, .doc)
  - `text`: (Tùy chọn) Chuỗi văn bản nếu không upload file
- **Response mẫu:**
```json
{
  "status": "success",
  "filename": "my_cv.pdf",
  "extracted": {
    "skills": ["Python", "React", "SQL"],
    "experience_years": 2.5,
    "education_level": 3,
    "education_label": "Đại học",
    "text_length": 1420,
    "preview_text": "Họ và tên: Nguyễn Văn A..."
  }
}
```

---

### 1.3 Tính lại điểm tương thích theo Job (Rescore Job)
- **URL:** `/api/match/rescore/<int:job_id>/`
- **Method:** `POST`
- **Quyền hạn:** Employer sở hữu tin tuyển dụng hoặc Admin
- **Chức năng:** Tái chấm điểm toàn bộ ứng viên theo mô hình AI mới nhất, tự động sắp xếp thứ hạng giảm dần theo điểm và trả về danh sách cập nhật trực tiếp cho bảng điều khiển mà không cần reload trang.
- **Response mẫu:**
```json
{
  "status": "success",
  "message": "Đã tính lại điểm tương thích cho 5 hồ sơ.",
  "rescored_count": 5,
  "applications": [
    {
      "id": 12,
      "candidate_name": "Trần Thị B",
      "location": "Hà Nội",
      "matching_score": 92.5,
      "method": "ml",
      "matched_skills": ["Python", "SQL"],
      "missing_required_skills": [],
      "status": "APPLIED",
      "status_display": "Đã ứng tuyển",
      "resume_url": "/media/resumes/cv_b.pdf"
    }
  ]
}
```

---

### 1.4 Cập nhật trạng thái ứng viên (Update Status)
- **URL:** `/api/applications/<int:app_id>/status/`
- **Method:** `POST`
- **Quyền hạn:** Employer sở hữu tin ứng tuyển hoặc Admin
- **Body:** `{"status": "INTERVIEW"}` (Các giá trị hợp lệ: `APPLIED`, `REVIEWING`, `INTERVIEW`, `ACCEPTED`, `REJECTED`, `WITHDRAWN`)
- **Response mẫu:**
```json
{
  "status": "success",
  "application_id": 12,
  "new_status": "INTERVIEW",
  "new_status_display": "Phỏng vấn"
}
```

---

## 2. Business Intelligence (BI) Analytics APIs

### 2.1 Tổng quan KPI (BI Summary)
- **URL:** `/api/bi/summary/`
- **Method:** `GET`
- **Response mẫu:**
```json
{
  "status": "success",
  "data": {
    "total_candidates": 115,
    "total_jobs": 50,
    "open_jobs": 42,
    "total_applications": 200,
    "interview_rate": 35.5,
    "accepted_rate": 18.0,
    "average_matching": 68.4,
    "matching_method": "AI Matching · Gradient Boosting"
  }
}
```

---

### 2.2 Phân tích Cung - Cầu Kỹ Năng (BI Skills)
- **URL:** `/api/bi/skills/?limit=8`
- **Method:** `GET`
- **Response mẫu:**
```json
{
  "status": "success",
  "count": 8,
  "data": [
    {
      "name": "Python",
      "demand": 24,
      "supply": 18,
      "gap": 6
    },
    {
      "name": "SQL",
      "demand": 30,
      "supply": 25,
      "gap": 5
    }
  ]
}
```

---

### 2.3 Phân bố mức lương theo chức danh (BI Salary)
- **URL:** `/api/bi/salary/?limit=7`
- **Method:** `GET`
- **Response mẫu:**
```json
{
  "status": "success",
  "data": [
    {
      "title": "Data Engineer",
      "count": 6,
      "min": 18000000.0,
      "max": 35000000.0,
      "average": 26500000.0
    }
  ]
}
```

---

### 2.4 Phễu tuyển dụng (BI Funnel)
- **URL:** `/api/bi/funnel/`
- **Method:** `GET`
- **Response mẫu:**
```json
{
  "status": "success",
  "total": 200,
  "rejected": 30,
  "stages": [
    {"stage": "Hồ sơ ứng tuyển", "count": 200, "rate": 100.0},
    {"stage": "Đang xem xét / Đạt sơ tuyển", "count": 135, "rate": 67.5},
    {"stage": "Mời phỏng vấn", "count": 71, "rate": 35.5},
    {"stage": "Trúng tuyển (Offer)", "count": 36, "rate": 18.0}
  ]
}
```

---

### 2.5 Xu hướng tuyển dụng theo thời gian (BI Trend)
- **URL:** `/api/bi/trend/?days=30`
- **Method:** `GET`
- **Response mẫu:**
```json
{
  "status": "success",
  "labels": ["04/10", "05/10", "...", "02/11"],
  "jobs": [1, 0, 3, 2, 4],
  "applications": [5, 8, 12, 10, 15]
}
```
