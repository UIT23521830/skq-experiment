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
| QĐ1/R1 | Review 12 | Xác nhận trực tiếp | CQ là dữ liệu chính | `configs/cq_v1/*`, `data/adapters/course_quality_v1.py` | `EV-CQ-SCREEN-RHO2-001`; G00/G02 | VERIFIED_DEV_CONFIRMATORY_BLOCKED_ROOT_ID |
| QĐ2/R2/O6 | Review 12 | Xác nhận trực tiếp | Một SKQ-PC; tối đa ba candidate dev | `methods/registry.py`, `config.py`, `proposed/skq_pc.py` | `EV-CQ-SCREEN-RHO2-001`; G00/G11 | VERIFIED_DEV_REVISION_REQUIRED |
| QĐ3/O1 | Review 12 | Xác nhận trực tiếp | Split theo khóa, temporal ưu tiên, SGKF fallback | `data/cq_protocol.py`, `data/adapters/course_quality_v1.py` | `EV-CQ-SCREEN-RHO2-001`; G03 | VERIFIED_DEV_PROVISIONAL_COURSE_ID |
| QĐ5 | Review 12 | Xác nhận trực tiếp | Định vị claim theo kết quả dev | freeze/report | M1 evidence | PLANNED |
| QĐ6/O2/O3 | Review 12 | Xác nhận trực tiếp | Seed, bootstrap, Pareto, không suy non-inferiority từ point estimate | `training/statistics.py`, `training/completeness.py`, `docs/statistics_protocol_v2.json` | `EV-CQ-SCREEN-RHO2-001`; G13 | DEV_THREE_SEEDS_NO_ROOT_BOOTSTRAP |
| QĐ7/QĐ17/O10/O18 | Review 12–13 | Xác nhận trực tiếp | Privacy, tag, PR, dữ liệu riêng | archive/audit | G01 | BLOCKED_REMEDIATION |
| QĐ8/QĐ16/O8/O15 | Review 12–13 | Xác nhận trực tiếp | Đo thời gian; operations chỉ diagnostic; khai báo wall-clock và GPU-giờ | `resources.py`, `experiments/resource_calibration.py`, `experiments/environment.py` | `EV-CQ-SCREEN-RHO2-001`; G09 | MEASURED_DEV_WAITING_CALIBRATION |
| QĐ9/O13 | Review 12–13 | Xác nhận trực tiếp | Dòng gốc là enrollment | CQ protocol, CQ v1 adapter | `EV-CQ-SCREEN-RHO2-001`; D09 | VERIFIED_DEV_ENROLLMENT_ROOT_ID_BLOCKED |
| QĐ10–QĐ11 | Review 12 | Xác nhận trực tiếp | Qc/Yc và UL/EC hai cấp | course metrics | G04 | IN_PROGRESS |
| QĐ12 | Review 13 | Xác nhận trực tiếp | Headroom chọn rho* trên dev | statistics/config | `EV-CQ-SCREEN-RHO2-001`; headroom decision rho*=2% | VERIFIED_DEV_CONFIRMATORY_BLOCKED_ROOT_ID |
| QĐ13/Y8 | Review 13 | Xác nhận trực tiếp | Test mới chỉ mở sau M0 và M1 hợp lệ | `experiments/freeze.py`, `experiments/runner.py`, `cli.py` | `tests/test_freeze_v4.py`; manifest thật còn thiếu | IMPLEMENTED_WAITING_DATA |
| QĐ14/Y11 | Review 13 | Xác nhận trực tiếp | CoreTab-XGB OVA phải ghi adapted | `methods/adapted/coretab_ova.py` | quota/no-pad tests và local upstream toy | IMPLEMENTED_TESTED_LOCAL |
| QĐ15/O11/O14 | Review 13 | Xác nhận trực tiếp | Effective weights mean one cho mọi run | weights/evaluator | G06 | IMPLEMENTED_TESTED |
| O16/Y5 | Review 13 | Xác nhận trực tiếp | Tune một lần, early stopping chỉ dùng dev | learners/evaluator/runner | `EV-CQ-SCREEN-RHO2-001`; G08 | VERIFIED_XGB_DEV_ONLY |
| O17 | Review 13 | Xác nhận trực tiếp | ID không làm tọa độ selector | CQ protocol/runner/feature contract | `EV-CQ-SCREEN-RHO2-001`; G07 | VERIFIED_DEV |
| O4 | Review 12–13 | Xác nhận trực tiếp | Synthetic ra khỏi phần chính | `config.py`, registry | G00 config tests | IMPLEMENTED_TESTED |
| O5 | Review 12–13 | Xác nhận trực tiếp | Bổ sung sáu baseline | controls + `methods/adapted/modern_baselines.py` | `EV-G10-FIDELITY-001`; Kaggle T4 strict toy 10/10 | VERIFIED_G10_KAGGLE_T4 |
| Y1–Y3/Y6–Y10/Y12–Y16 | Review 12–13 | Xác nhận trực tiếp | Số liệu, tên, seed, owner, reporting | registry/reports/docs | G16 | PLANNED |
| G16/TRACE-01 | V2 §19/§23 | Suy luận triển khai theo review | Evidence và claim phải truy được run/config/split/commit, không chỉ báo cáo tay | `reports/evidence.py`, `scripts/audit_claim_ledger.py` | `EV-CQ-SCREEN-RHO2-001`; 64 run_id, config/split/commit và artifact hashes | VERIFIED_DEV_EVIDENCE |
| G00–G16/GATE-01 | V2 §23 | Suy luận triển khai theo review | Mỗi gate giữ điều kiện/evidence/fail action và trạng thái lỗi riêng | `experiments/quality_gates.py`, `docs/quality_gates_v2.json` | `tests/test_quality_gates.py`; evidence map thật còn thiếu | IMPLEMENTED_WAITING_EVIDENCE |
| G10/FID-01 | Review 12 §7.6/§7.11 | Xác nhận trực tiếp + adapter khai báo | Khóa official source, commit, patch/adaptation và toy reproduction; không proxy | `official_repos.lock.json`, `method_fidelity_v2.json`, `run_method_fidelity_toys.py` | `EV-G10-FIDELITY-001`; commit `fb4bd97a47f1c897b029199a4648b9b39d9d0317`; strict audit 10/10, không finding | VERIFIED_G10_10_OF_10 |
| G13/MISS-01 | Review 12 O2/O3 | Suy luận triển khai theo yêu cầu không bỏ lỗi | Failed/timeout/blocked giữ trong mẫu số; không impute 0; thiếu ô làm hypothesis not-estimable | `training/completeness.py`, `statistics_protocol_v2.json` | `tests/test_completeness.py` | IMPLEMENTED_TESTED |
| INF-01 | V2 §13.3 + deviation nội bộ 17/10 | Suy luận triển khai chờ duyệt | CoreTab-cell đã runnable ở dev-only; `test_locked=true`, explicit acknowledgement, không được freeze/confirmatory | `methods/proposed/skq_pc.py`, registry, config | `tests/test_skq_pc.py`, metadata/freeze gate tests | IMPLEMENTED_DEV_ONLY_WAITING_APPROVAL |
| INF-02 | V2 §12 | Suy luận triển khai | Dùng prediction interval khi calibration | calibration | calibration tests | PLANNED |
| INF-03 | V2 §20 | Suy luận triển khai | Audit cả Git history, không chỉ working tree | audit script | privacy evidence | IMPLEMENTED_FINDINGS |

## Quy tắc cập nhật

Mỗi dòng khi chuyển sang `VERIFIED_DEV` phải có `evidence_id`, commit và test cụ
thể. Khi có `run_id`, không thay bằng mô tả thủ công. Evidence dòng/indices/weights
được giữ private; tài liệu public chỉ chứa manifest và hash.

