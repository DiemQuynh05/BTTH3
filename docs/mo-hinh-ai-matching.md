# Mô hình AI Matching: phân tích CV và điểm tương thích

## 1. Mục tiêu

Với mỗi cặp **ứng viên – tin tuyển dụng**, hệ thống:

1. Trích xuất nội dung CV (PDF/DOCX) và nhận diện kỹ năng, số năm kinh nghiệm, trình độ học vấn.
2. Tính **Matching Score 0–100** = xác suất (×100) ứng viên được mời phỏng vấn/nhận việc, do mô hình
   Machine Learning dự đoán.
3. Giải thích điểm: kỹ năng khớp, kỹ năng bắt buộc còn thiếu và các yếu tố ảnh hưởng nhiều nhất.

Toàn bộ chạy cục bộ bằng scikit-learn, không gọi API AI bên ngoài.

## 2. Kiến trúc

```text
CV (PDF/DOCX) ──► cv_parser.extract_text ──► Resume.resume_text
                                │
Hồ sơ ứng viên + CV ──► CandidateDoc ─┐
                                      ├─► features.feature_matrix (10 đặc trưng) ─► classifier ─► xác suất ─► điểm 0–100
Tin tuyển dụng + JobSkill ─► JobDoc ──┘                                                         └─► giải thích
```

| Thành phần | File | Vai trò |
|---|---|---|
| Chuẩn hóa văn bản | `applications/ai/text.py` | Bỏ dấu tiếng Việt, chữ thường, giữ `c#`, `c++`, `.net` |
| Nhận diện kỹ năng | `applications/ai/skills.py` | Từ điển ~50 kỹ năng + biến thể (`ReactJS`→React, `IELTS`→Tiếng Anh), kết hợp bảng `Skill` trong DB; suy luận (Django ⇒ Python) |
| Phân tích CV | `applications/ai/cv_parser.py` | Trích xuất text PDF (pypdf) / DOCX (python-docx); số năm kinh nghiệm; bậc học |
| Đặc trưng | `applications/ai/features.py` | Tính 10 đặc trưng cho cặp CV – JD |
| Mô hình | `applications/ai/model.py` | TF-IDF, chọn mô hình, đánh giá, lưu/tải, giải thích |
| Dữ liệu mô phỏng | `applications/ai/synthetic.py` | Sinh dữ liệu huấn luyện cold-start |
| Tích hợp Django | `applications/matching.py`, `candidates/services.py` | Chuyển ORM → `CandidateDoc`/`JobDoc`, chấm điểm, fallback rule-based |

## 3. Phân tích CV

- **Văn bản:** PDF dạng văn bản (tối đa 20 trang) và DOCX (kể cả bảng). File `.doc`, PDF ảnh scan hoặc
  file hỏng trả về rỗng; CV vẫn được lưu và `resume_text` cũ không bị ghi đè.
- **Kỹ năng:** so khớp theo ranh giới từ trên văn bản đã bỏ dấu, nên `html` không bị nhận nhầm thành
  `ml`, `javascript` không thành `java`.
- **Kinh nghiệm:** ưu tiên câu nêu rõ ("3 năm kinh nghiệm", "6 tháng kinh nghiệm"); nếu không có, cộng
  các khoảng thời gian (`03/2021 - nay`) **chỉ trong mục Kinh nghiệm**, gộp khoảng trùng, bỏ qua mốc
  thời gian ở mục Học vấn.
- **Học vấn:** THPT/Trung cấp (1) → Cao đẳng (2) → Đại học (3) → Thạc sĩ (4) → Tiến sĩ (5).

Kết quả lưu ở `Resume.parsed_data` và hiển thị trên trang hồ sơ ứng viên.

## 4. Đặc trưng

| Đặc trưng | Cách tính |
|---|---|
| `required_skill_coverage` | Tỷ lệ kỹ năng bắt buộc của JD mà ứng viên có |
| `preferred_skill_coverage` | Tỷ lệ kỹ năng ưu tiên mà ứng viên có |
| `skill_overlap` | Jaccard giữa kỹ năng ứng viên và kỹ năng JD |
| `text_similarity` | Cosine TF-IDF (unigram + bigram) giữa nội dung CV và JD |
| `title_similarity` | Cosine TF-IDF giữa chuyên ngành ứng viên và chức danh JD |
| `experience_gap` | (năm KN ứng viên − năm KN yêu cầu) / 5, giới hạn [−1, 1] |
| `meets_experience` | 1 nếu đạt số năm yêu cầu |
| `education_gap` | Chênh lệch bậc học / 2, giới hạn [−1, 1]; 0 nếu thiếu thông tin |
| `location_fit` | 1: cùng thành phố hoặc remote; 0.5: hybrid khác thành phố/không rõ; 0: onsite khác thành phố |
| `salary_fit` | 1 nếu lương mong muốn ≤ mức trần; giảm tuyến tính khi vượt; 0.5 nếu không rõ |

Kỹ năng ứng viên = kỹ năng khai báo (`CandidateSkill`) ∪ kỹ năng trích xuất từ CV/hồ sơ. Kỹ năng JD lấy
từ `JobSkill`; nếu tin chưa khai báo kỹ năng thì trích xuất từ nội dung JD. Số năm yêu cầu = max(mức theo
cấp bậc ENTRY 0 / JUNIOR 1 / MID 3 / SENIOR 5, `minimum_years` của kỹ năng bắt buộc).

## 5. Huấn luyện

### Bài toán

Phân loại nhị phân: nhãn 1 = hồ sơ được mời phỏng vấn/nhận việc, 0 = bị từ chối. Điểm = P(nhãn 1) × 100.

### Dữ liệu

| Nguồn (`--source`) | Mô tả |
|---|---|
| `synthetic` (mặc định) | 4.000 cặp CV – JD mô phỏng cho 12 nhóm vị trí. Văn bản CV/JD được sinh ra rồi đi qua **cùng bộ phân tích CV** như dữ liệu thật. Nhãn sinh từ hàm quyết định ẩn dựa trên thông tin *thật* của ứng viên (kỹ năng thật, vai trò thật, kinh nghiệm thật) + nhiễu, trong khi mô hình chỉ thấy những gì trích xuất được từ văn bản. |
| `database` | Hồ sơ ứng tuyển thật: `INTERVIEW`/`ACCEPTED` = 1, `REJECTED` = 0 (cần ≥ 30 hồ sơ mỗi nhãn, chỉnh bằng `--min-labels`). |
| `combined` | Gộp hai nguồn trên. |

Trạng thái hồ sơ do `seed_demo_data` tạo được gán theo vòng lặp, không phản ánh mức độ phù hợp, nên
**không dùng làm nhãn huấn luyện**.

### Quy trình

1. Fit TF-IDF trên văn bản huấn luyện và văn bản JD/CV đang có trong DB (không dùng nhãn).
2. Tách 80/20 có phân tầng.
3. Cross-validation 5 fold (ROC-AUC) trên tập train cho hai mô hình: Logistic Regression (có chuẩn hóa)
   và HistGradientBoosting; chọn mô hình có ROC-AUC cao hơn.
4. Đánh giá trên tập kiểm thử 20%, sau đó huấn luyện lại trên toàn bộ dữ liệu để triển khai.
5. Lưu `matching_model.joblib` và báo cáo `matching_model.json`.

### Kết quả (lần chạy `train_matching_model` mặc định, seed 42, trên dữ liệu demo)

| Chỉ số | Giá trị |
|---|---|
| CV ROC-AUC – Logistic Regression | 0.917 |
| CV ROC-AUC – HistGradientBoosting (được chọn) | 0.919 |
| Hold-out ROC-AUC | 0.927 |
| Accuracy / Precision / Recall / F1 | 0.849 / 0.799 / 0.841 / 0.820 |
| Brier score | 0.106 |

Các chỉ số này đo trên **nhãn mô phỏng**: chúng cho thấy pipeline học được tín hiệu từ văn bản CV/JD
có nhiễu trích xuất, **không** phải độ chính xác trên quyết định tuyển dụng thật. Số liệu thay đổi nhẹ
theo dữ liệu trong DB (do từ vựng TF-IDF). Cần huấn luyện lại với `--source database`/`combined` khi
có đủ kết quả tuyển dụng thật.

Trên 220 hồ sơ demo sau `rescore_applications`: trung vị điểm là 93.2 khi ứng viên có đủ 2/2 kỹ năng
bắt buộc (57 hồ sơ), 36.0 khi có 1/2 (36 hồ sơ) và 3.8 khi có 0/2 (127 hồ sơ).

## 6. Giải thích điểm

`Application.matching_explanation` lưu:

- `matched_skills`, `missing_required_skills`, `missing_preferred_skills`, `required_skills` ("2/3").
- `features`: giá trị 10 đặc trưng.
- `top_factors`: 4 đặc trưng ảnh hưởng nhất. Tác động của mỗi đặc trưng = điểm hiện tại − điểm khi thay
  đặc trưng đó bằng giá trị trung bình lúc huấn luyện (phương pháp occlusion, dùng được cho cả hai loại mô hình).
- `method` (`ml` hoặc `rule_based`), `model`, `trained_at`, `data_source`, `probability`.

## 7. Tích hợp trong hệ thống

| Thời điểm | Hành vi |
|---|---|
| Ứng viên tải CV | Trích xuất văn bản, lưu `resume_text` + `parsed_data`, hiển thị kỹ năng nhận diện được |
| Ứng viên xem tin | Hiển thị điểm phù hợp và kỹ năng bắt buộc còn thiếu |
| Ứng viên nộp hồ sơ | Tính và lưu `matching_score`, `matching_explanation` |
| Nhà tuyển dụng | `/employers/jobs/<id>/applicants/`: xếp hạng ứng viên, nút "Tính lại điểm" |
| BI Dashboard | Hiển thị phương pháp đang dùng và điểm trung bình |

Nếu chưa có file mô hình, file không tương thích, hoặc mô hình lỗi khi chấm, hệ thống tự dùng thuật toán
rule-based cũ (`calculate_rule_based_score`).

## 8. Vận hành

```powershell
python manage.py train_matching_model [--source synthetic|database|combined] [--samples 4000] [--output path]
python manage.py rescore_applications [--job ID] [--skip-resumes]
```

File mô hình nằm trong `ml_models/` (không commit, đã thêm vào `.gitignore`); cần huấn luyện lại khi đổi
phiên bản scikit-learn hoặc thay đổi danh sách đặc trưng.

## 9. Hạn chế

- Nhãn mô phỏng phản ánh giả định thiết kế, không phải hành vi nhà tuyển dụng thật.
- TF-IDF chỉ so khớp từ vựng, chưa hiểu ngữ nghĩa sâu (ví dụ đồng nghĩa ngoài từ điển kỹ năng).
  Có thể thay bằng sentence embedding đa ngôn ngữ khi chấp nhận thêm phụ thuộc (PyTorch).
- Từ điển kỹ năng cần bổ sung khi mở rộng sang ngành nghề mới.
- Chưa OCR cho CV dạng ảnh scan, chưa đọc file `.doc`.
