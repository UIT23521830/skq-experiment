# CQ V3 — Checklist xin GO M0 ngày 21/10/2026

## Phạm vi khóa

- Dữ liệu chính: `phase-features-v3/course_random_split`.
- M0 chỉ dùng train/dev; gói Kaggle rút gọn không chứa `test.parquet`.
- Target chính: `y_alpha_1`; E/G/A tương ứng q dưới 0,2, từ 0,2 đến dưới
  0,4, và từ 0,4 trở lên.
- Learner view có 57 numeric và 5 categorical; selector view loại
  `phase_fraction` và toàn bộ mã categorical, còn 56 numeric.
- Một phép median/mean/std được fit trên Pool B train gộp P1--P4 rồi áp cho
  mọi dev phase. Không dùng scaler riêng phase của nguồn V3.

## Bốn điều kiện GO theo Review 12--13/10

| Điều kiện | Trạng thái hiện tại | Evidence đã kiểm chứng | Còn thiếu |
|---|---|---|---|
| Data card, split, D01--D07 và D09--D12 | `CONDITIONAL` | 61/61 test code đạt; D02 course-ID bằng majority; D03 đã chạy từ pre-imputation raw; D06 có 20/20 ca cutoff đạt; 0 course giao train/dev | D04 chạy lại trên T4; xác nhận `course_id == course_root_id`; cô duyệt deviation `course_random` thay temporal/SGKF |
| FullTrain-A/B, LR/XGB, UL/EC, natural/balanced | `RUNNING_V3` | Config V3 đã khóa; Pool B train 513.628 snapshot và dev 65.204 snapshot | Chờ archive Kaggle V3; FullTrain-A không có trong nguồn, cần cung cấp hoặc miễn/đổi định nghĩa bằng văn bản |
| Timing QĐ16 và lịch dev/test | `PARTIAL_9_OF_13` | Chín selector đã đủ 50k/200k/800k x 3 ở rho 0,5%; 17/17 test timing đạt | Kernel Thinning và ba SKQ candidate chưa đủ checkpoint; chưa có upper-bound schedule toàn panel |
| Khung LNCS, đề cương v2, BibTeX, novelty ledger | `READY_FOR_M0_REVIEW` | `paper/icc_review_m0_v1/main.tex`, `references.bib`, ledger và báo cáo xin GO | Claim phương pháp/test vẫn để trống cho đến sau M1 freeze |

## Evidence V3 cục bộ trước Kaggle

- Bundle: `data/phase_features_v3_m0_bundle/cq_v3_m0_dev.zip`.
- Kích thước: 104.580.461 byte.
- SHA-256:
  `9F60946C140B7E16EE1F9BB3D94FC21BBEC898F476BE669416EBD6E4C55995A6`.
- Chọn 37 file nguồn, 105.132.365 byte; loại toàn bộ test, features shard,
  sequences, `_stage`, target toàn cohort và split mặc định bị overlap course.
- D02 P4: Macro-F1 course-only `0,2692073245`, đúng bằng majority.
- D03 missing-mask probe, không đưa mask vào production X:

| Phase | Macro-F1 | Macro OVR ROC-AUC |
|---|---:|---:|
| P1 | 0,230515 | 0,636981 |
| P2 | 0,274805 | 0,601373 |
| P3 | 0,286852 | 0,601748 |
| P4 | 0,289285 | 0,602711 |
| Trung bình AUC | -- | **0,610703** |

- D06: lấy xác định 5 ca mỗi phase; 20/20 có
  `max_feature_event_time <= cutoff_time` và `n_out_of_window_events=0`.
  Bảng có ID chỉ nằm trong artifact private; báo cáo công khai chỉ giữ SHA-256
  của cặp learner--course.

## Blocker cần giảng viên quyết định

1. Có chấp thuận dùng `course_id` làm group unit khi nhóm dữ liệu xác nhận mỗi
   course chỉ mở một lần, hay bắt buộc tạo `course_root_id` riêng?
2. Có chấp thuận split ngẫu nhiên 70/10/20 theo course, 0 course overlap, cho
   M1; hay yêu cầu nhóm dữ liệu dựng lại temporal/SGKF?
3. FullTrain-A chưa có full-behavior table. Cô muốn cung cấp nguồn, cho phép
   bỏ FullTrain-A, hay duyệt một định nghĩa thay thế? P4=90% không được tự gọi
   là FullTrain-A.
4. Có cho phép tiếp tục M1 trên dev trong khi QĐ16 ghi Kernel Thinning là
   timeout/censored và chạy hoàn tất ba candidate, hay phải đóng đủ 13/13 trước?
5. Kaggle dataset rút gọn sẽ đặt Private. Việc này có đủ cho xác nhận privacy
   M0 trong khi lịch sử Git còn ba object XLSX, hay cần repo public sạch riêng?

## Quyết định xin duyệt

Nhóm xin **GO M0 có điều kiện để tiếp tục M1 trên train/dev và hoàn thiện bản
thảo**, với ba ràng buộc:

1. test tiếp tục khóa và không có metric test;
2. không freeze confirmatory trước khi chốt group unit và split protocol;
3. không dùng từ `SOTA`, `vượt trội`, `đầu tiên` hoặc claim tính mới trước khi
   novelty ledger và M1 freeze hoàn tất.

GO đầy đủ chỉ được ghi sau khi archive Kaggle V3 đạt, các quyết định 1--3 ở trên
có phản hồi bằng văn bản, và QĐ16 có quyết định đủ cho cả 13 phương pháp.
