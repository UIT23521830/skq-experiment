# Traceability Review 12–13/10/2026

## Kiểm soát

```text
traceability_schema_version: 1
plan_version: 2.0.0-draft
base_commit: acd2d9f62d7f199abef16eb943b28f9c0c9e145e
review_2026_10_12_sha256: 3C48CAAA4024FF9A7D19F948428142586BE0097849319B45B056BE39880538AB
review_2026_10_13_sha256: 35F6CE05910ACEB5777610B482FC9D12BD14FF35E0E0FD8590D26C79970E8EA2
```

Đây là sổ truy vết triển khai, không phải nơi tự thay đổi quyết định của review.
`Xác nhận trực tiếp` nghĩa là câu chữ có trong review. `Suy luận triển khai` là lựa
chọn kỹ thuật cần thiết để hiện thực yêu cầu; mọi suy luận phải được ghi vào báo
cáo thực hiện và không được tạo claim học thuật mới.

| ID | Nguồn | Loại | Yêu cầu | Code chính | Test/evidence | Trạng thái |
|---|---|---|---|---|---|---|
| QĐ1/R1 | Review 12 | Xác nhận trực tiếp | CQ là dữ liệu chính | `configs/cq_v1/*` | G00/G02 | PLANNED |
| QĐ2/R2/O6 | Review 12 | Xác nhận trực tiếp | Một SKQ-PC; tối đa ba candidate dev | `methods/registry.py`, `proposed/skq_pc.py` | G00/G11 | IN_PROGRESS |
| QĐ3/O1 | Review 12 | Xác nhận trực tiếp | Split theo khóa, temporal ưu tiên, SGKF fallback | `data/cq_protocol.py` | G03 | PLANNED |
| QĐ5 | Review 12 | Xác nhận trực tiếp | Định vị claim theo kết quả dev | freeze/report | M1 evidence | PLANNED |
| QĐ6/O2/O3 | Review 12 | Xác nhận trực tiếp | Seed, bootstrap, Pareto, không suy non-inferiority từ point estimate | statistics/report | G13 | PLANNED |
| QĐ7/QĐ17/O10/O18 | Review 12–13 | Xác nhận trực tiếp | Privacy, tag, PR, dữ liệu riêng | archive/audit | G01 | IN_PROGRESS |
| QĐ8/QĐ16/O8/O15 | Review 12–13 | Xác nhận trực tiếp | Đo thời gian; operations chỉ diagnostic | `resources.py`, calibration | G09 | PLANNED |
| QĐ9/O13 | Review 12–13 | Xác nhận trực tiếp | Dòng gốc là enrollment | CQ protocol | D09 | BLOCKED_EXTERNAL |
| QĐ10–QĐ11 | Review 12 | Xác nhận trực tiếp | Qc/Yc và UL/EC hai cấp | course metrics | G04 | PLANNED |
| QĐ12 | Review 13 | Xác nhận trực tiếp | Headroom chọn rho* trên dev | statistics/config | headroom evidence | PLANNED |
| QĐ13/Y8 | Review 13 | Xác nhận trực tiếp | Test mới chỉ mở sau freeze hợp lệ | freeze/runner | G14/G15 | PLANNED |
| QĐ14/Y11 | Review 13 | Xác nhận trực tiếp | CoreTab-XGB OVA phải ghi adapted | `methods/adapted` | G12 | PLANNED |
| QĐ15/O11/O14 | Review 13 | Xác nhận trực tiếp | Effective weights mean one cho mọi run | weights/evaluator | G06 | PLANNED |
| O16/Y5 | Review 13 | Xác nhận trực tiếp | Tune một lần, early stopping chỉ dùng dev | learners/evaluator/runner | G08 | PLANNED |
| O17 | Review 13 | Xác nhận trực tiếp | ID không làm tọa độ selector | CQ protocol/runner | G07 | PLANNED |
| O4 | Review 12–13 | Xác nhận trực tiếp | Synthetic ra khỏi phần chính | config/registry | G00 | PLANNED |
| O5 | Review 12–13 | Xác nhận trực tiếp | Bổ sung sáu baseline | method adapters | G10 | PLANNED |
| Y1–Y3/Y6–Y10/Y12–Y16 | Review 12–13 | Xác nhận trực tiếp | Số liệu, tên, seed, owner, reporting | registry/reports/docs | G16 | PLANNED |
| INF-01 | V2 §13.3 | Suy luận triển khai | CoreTab-cell chỉ là candidate disabled chờ duyệt | registry | metadata test | IN_PROGRESS |
| INF-02 | V2 §12 | Suy luận triển khai | Dùng prediction interval khi calibration | calibration | calibration tests | PLANNED |
| INF-03 | V2 §20 | Suy luận triển khai | Audit cả Git history, không chỉ working tree | audit script | privacy evidence | PLANNED |

## Quy tắc cập nhật

Mỗi dòng khi chuyển sang `VERIFIED_DEV` phải có `evidence_id`, commit và test cụ
thể. Khi có `run_id`, không thay bằng mô tả thủ công. Evidence dòng/indices/weights
được giữ private; tài liệu public chỉ chứa manifest và hash.

