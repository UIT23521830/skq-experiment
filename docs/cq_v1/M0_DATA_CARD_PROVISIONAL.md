# CQ v1 — Data card và kiểm tra M0 (provisional)

> Artifact tự sinh từ `scripts/audit_cq_v1_m0.py`. Không chứa ID thật và không dùng dự đoán test.

- Dataset version: `phase-features-v2-cutoffs-v2-shared-targets-2026-10-20`
- Target: `y_alpha_1` từ `q_alpha_1`; ngưỡng 0,2/0,4; giá trị nhỏ là tốt.
- `n_min=30`, `delta_C=0.01`.
- Group unit: `course_id_provisional`.
- Confirmatory eligible: `false`.

## Hai feature view theo O17/QĐ3

- Selector view: `56` feature hành vi; không chứa cột mã.
- Learner view: `62` feature; giữ `field_set_code, gender_code, learner_code, school_set_code, teacher_set_code` theo TEMPO-DQ.
- `course_id`, target và target-derived columns không nằm trong hai view.

## Phân bố

| Split | Enrollment | User | Course | E | G | A | Course < n_min | ICC(1) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| train | 248652 | 226900 | 1902 | 7920 | 43777 | 196955 | 943 | 0.267405 |
| dev | 31028 | 30524 | 266 | 177 | 12047 | 18804 | 205 | 0.460239 |
| test | 28318 | 27510 | 512 | 371 | 4770 | 23177 | 377 | 0.442543 |

## Hằng số train và sàn EC dev

- mu_E=0.07373661, mu_G=0.32728126, mu_A=0.64609105
- Oracle floor EC dev (n_min): `0.05878932156021635` trên `61` khóa.

## Checks 1–12

| Check | Status | Lý do/evidence |
|---|---|---|
| D01_size_distribution_split | PASS | rows/users/courses/classes emitted below |
| D02_id_only_probe | PASS | course-only dev Macro-F1 equals majority and all dev course IDs are unseen |
| D03_missingness_probe | BLOCKED | model-ready snapshot is already imputed; raw pre-imputation matrix is required |
| D04_shuffled_labels | BLOCKED | requires FullTrain-B development run |
| D05_majority_baseline | PASS | majority Macro-F1 emitted for P1-P4 |
| D06_cutoff_manual_20 | BLOCKED | requires raw event timestamps for 20 sampled enrollment-course pairs |
| D07_weight_contract | PASS_CODE | covered by unit tests; run evidence still required |
| D08_baseline_fidelity | DEFERRED_M1 | review explicitly allows completion before M1 |
| D09_unit_label | PASS |  |
| D10_no_label_in_X | PASS |  |
| D11_course_recompute | PASS_GENERATED | Qc/Yc recomputed from enrollment q; this audit creates the first data-card values |
| D12_protocol_constants | PASS |  |
| course_root_contract | BLOCKED | awaiting written confirmation that each course_id opens once |

## Giới hạn chưa được phép suy đoán

- Chưa xác nhận `course_id == course_root_id` bằng văn bản.
- Chưa có raw event để kiểm thủ công cutoff và missingness probe.
- Chưa có FullTrain-A (full-behavior) trong snapshot Pool B.
- Test vẫn khóa; thống kê phân bố test không phải đánh giá mô hình.
