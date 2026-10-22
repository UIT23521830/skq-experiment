# CQ V3 M0 — biên bản preflight trước Kaggle

**Thời điểm kiểm tra:** 22/10/2026 (Asia/Saigon)  
**Nhánh:** `cq-v1-protocol-fixes`  
**Commit chứa pipeline Kaggle:** `81e1181a8ca25b0dceb9c387a3e3811a6f2d3466`

## 1. Gói upload tối thiểu

File: `data/phase_features_v3_m0_bundle/cq_v3_m0_dev.zip`

| Thuộc tính | Kết quả |
|---|---:|
| Kích thước ZIP | 104.580.461 byte |
| SHA-256 | `9F60946C140B7E16EE1F9BB3D94FC21BBEC898F476BE669416EBD6E4C55995A6` |
| File nguồn trong manifest | 37 |
| Tổng byte nguồn | 105.132.365 |
| Tổng entry trong ZIP | 39 |
| Sai kích thước/SHA-256 | 0 |
| Entry bị cấm | 0 |
| `test_locked` | `true` |
| `test_files_included` | `false` |

Phép kiểm độc lập đọc trực tiếp từng ZIP entry, tính lại SHA-256 và đối chiếu
`BUNDLE_MANIFEST.json`. Mẫu bị cấm gồm `test.parquet`, `features/`,
`sequences/` và `_stage/`.

## 2. Bộ kiểm thử M0

Bộ 61 kiểm thử được dùng làm bằng chứng trong báo cáo gồm 12 file contract mà
cell Kaggle chạy và bốn file kiểm tra hạ tầng M0/QĐ16:

- `test_course_quality_v1_adapter.py`
- `test_cq_m0_audit.py`
- `test_cq_raw_contract.py`
- `test_cq_protocol.py`
- `test_cq_patch_1013_contracts.py`
- `test_feature_views.py`
- `test_weights.py`
- `test_headroom.py`
- `test_cq_headroom_evidence.py`
- `test_course_metrics.py`
- `test_training_protocol.py`
- `test_cq_dev_endpoints.py`
- `test_resource_calibration.py`
- `test_resource_schedule.py`
- `test_privacy_audit.py`
- `test_quality_gates.py`

Kết quả local: **61/61 PASS**.

Riêng suite archive mới (`test_cq_v3_m0_archive_summary.py`) và hai suite liên
quan trực tiếp đã đạt **10/10 PASS**. Trình tổng hợp đã được thử với archive cũ
không đủ V3 và trả đúng `NOT_READY`, thay vì suy diễn GO.

## 3. Phạm vi bằng chứng

Preflight này chứng minh gói upload nguyên vẹn, không chứa test và code contract
đang đạt. Nó không thay thế kết quả chạy T4. Sau khi nhận archive Kaggle, phải
chạy `scripts/summarize_cq_v3_m0_archive.py`; chỉ khi trả
`READY_TO_REQUEST_CONDITIONAL_GO` mới ghép số liệu V3 vào báo cáo gửi cô.

Preflight cũng không tự đóng bốn blocker ngoài archive: xác nhận group unit,
phê duyệt split deviation, xử lý FullTrain-A và QĐ16 đầy đủ.
