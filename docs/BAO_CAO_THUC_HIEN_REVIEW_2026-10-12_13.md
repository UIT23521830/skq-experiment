# Nhật ký thực hiện Review 12–13/10/2026

Tài liệu này dùng để thu hoạch những gì đã làm và phân biệt quyết định của giảng
viên với suy luận kỹ thuật của nhóm. Chưa có mục nào trong file này tự tạo bằng
chứng confirmatory.

## Quy ước

- **Xác nhận trực tiếp:** làm đúng câu chữ review; không cần diễn giải thành đóng
  góp mới.
- **Suy luận triển khai:** lựa chọn kỹ thuật không được review chỉ rõ; phải nêu lý
  do, rủi ro, test và phạm vi claim.
- **Bằng chứng:** commit, test, evidence manifest hoặc run ID; không dùng nhận xét
  miệng thay bằng chứng.

## Nhật ký

### 14/10/2026 — Khóa kế hoạch và metadata nền

**Xác nhận trực tiếp đã áp dụng**

- Giữ riêng các trạng thái `failed`, `oom`, `timeout`, `blocked`, `na_contract`,
  không đổi lỗi thành success và không loại khỏi ledger.
- Giữ provenance theo commit/hash, artifact identity và không fallback âm thầm.
- P01–P05, P09–P11 không được xem là phương pháp confirmatory mới.
- CoreTab native là binary-only; OVA phải mang nhãn adapted.
- Tổng số candidate SKQ-PC dùng chọn dev không vượt ba.

**Suy luận triển khai**

- Thêm taxonomy machine-readable thay cho chỉ ghi chú tự do trong registry.
- Đăng ký ý tưởng CoreTab multiclass dưới mã exploratory bị vô hiệu hóa, để có thể
  viết contract/test toy nhưng không thể đi vào config confirmatory trước khi được
  chấp thuận.
- Thêm `.editorconfig` UTF-8 để docstring tiếng Việt nhất quán Windows/Kaggle.

### 14/10/2026 — Chuẩn hóa trọng số và tách operation khỏi gate

**Xác nhận trực tiếp đã áp dụng**

- Effective sample weight của FullTrain, subset thật và synthetic được chuẩn hóa
  mean bằng 1 sau khi nhân method weight với class weight.
- Số phép tính ước lượng chỉ còn là diagnostic; vượt ngưỡng cũ không tạo
  `predicted_timeout`.
- `predicted_oom`, `oom` và `timeout` vẫn là ba trạng thái riêng: RAM dự báo vẫn
  có thể chặn trước, còn RSS/thời gian thật được ResourceGuard kiểm tra khi chạy.

**Suy luận triển khai**

- Giữ khóa `max_estimated_operations` cũ để đọc được config lịch sử, nhưng đổi
  tên ý nghĩa trong evidence thành `legacy_reference_operations` và ghi rõ
  `decision_role=diagnostic_only`. Việc này tương thích ngược, không biến ngưỡng
  cũ thành tiêu chí loại mẫu.
- Chỉ ghi thống kê count/min/max/mean/sum/zero_count của weight vào cost artifact,
  không nhân bản cả vector trọng số trong bảng metric.

**Bằng chứng cục bộ**

- `tests/test_weights.py`: kiểm tra mean=1 và bất biến với phép nhân toàn cục.
- `tests/test_resources.py`: kiểm tra operation vượt mốc cũ vẫn được phép chạy.
- `tests/test_temporal_evaluation.py`: kiểm tra weight thực sự truyền vào learner
  và metadata cost đều có mean=1.

### 14/10/2026 — Contract cấu hình learner và early stopping

**Xác nhận trực tiếp đã áp dụng**

- Runner chỉ truyền split `dev` vào đường early stopping; không có tham số hay
  nhánh nào nhận `test` cho mục đích này.
- Tham số learner được khai báo một lần ở cấp experiment và dùng lại cho mọi
  phương pháp trong experiment đó.
- Config có `class_weight_policy` rõ ràng (`natural` hoặc `balanced`) và toàn bộ
  lựa chọn trên được serialize vào provenance.

**Suy luận triển khai**

- Không tự bật early stopping cho config lịch sử. Config V2 phải khai báo
  `early_stopping={enabled: true, source: dev, patience: ...}` để tránh âm thầm
  thay đổi nghĩa của các kết quả đã chạy trước review.
- Dùng cùng một khóa `patience`, sau đó ánh xạ sang `early_stopping_rounds` của
  XGBoost/CatBoost và `patience` của MLP. Đây là thống nhất giao diện thực thi,
  không phải tuyên bố ba learner có động lực tối ưu giống nhau.
- Ghi `best_iteration` khi thư viện cung cấp. Giá trị thiếu được giữ là `null`,
  không suy đoán từ tổng số estimator/epoch.

**Chưa hoàn tất**

- Chưa tune trên FullTrain-B vì CQ v1 chính thức chưa được freeze.
- Chưa có evidence của bộ siêu tham số thắng; vì vậy O16/Y5 vẫn ở trạng thái
  `IN_PROGRESS`, chưa được đánh dấu hoàn tất chỉ nhờ có code.

**Bằng chứng cục bộ**

- `tests/test_training_protocol.py`: dev-only, thiếu dev bị từ chối, ghi
  best_iteration và kiểm tra class-weight policy.
- `tests/test_config.py`: từ chối `source=test` và kiểm tra serialization.

### 14/10/2026 — Privacy audit public release

**Xác nhận trực tiếp đã áp dụng**

- Audit tách riêng finding của file đang track, object trong Git history và entry
  của archive; một nhóm lỗi không che hoặc ghi đè nhóm khác.
- Không đưa raw/processed CQ, prediction, row ID, selected indices, sample weights,
  credential hoặc notebook còn output vào gói public.
- Không rewrite lịch sử hay force-push tự động khi phát hiện finding.

**Kết quả audit repo hiện tại**

- Không thấy path dữ liệu CQ mức dòng trong danh sách finding.
- Phát hiện workbook `MA_TRAN_THUC_NGHIEM_SKQ_FULL.xlsx` đang được track và ba
  object cùng path trong lịch sử. Đây là vi phạm allowlist binary, chưa phải bằng
  chứng workbook chứa PII.
- Đã bỏ workbook khỏi Git index nhưng giữ nguyên file local. Lịch sử chưa thay đổi,
  nên G01 là `BLOCKED_REMEDIATION`, không được ghi pass.
- Chi tiết và hai phương án xử lý trước public release nằm tại
  `docs/PRIVACY_INCIDENT_2026-10-14.md`.

**Suy luận triển khai**

- Scan Git history theo object path để tránh đọc/xuất nội dung object nhạy cảm vào
  log. Việc kiểm nội dung credential được thực hiện trên file đang track và chỉ
  báo loại secret, không chép giá trị secret vào evidence.
- Repo private là giảm phơi nhiễm nhưng không thay thế privacy gate; trạng thái
  GitHub do nhóm xác nhận, script cục bộ không xem đó là bằng chứng tự động.

**Bằng chứng cục bộ**

- `scripts/audit_public_release.py` và `tests/test_privacy_audit.py`.
- Evidence local bị ignore: `artifacts/privacy/privacy_audit.json`.

### 14/10/2026 — Contract selector view và learner view

**Xác nhận trực tiếp đã áp dụng**

- Selector view chỉ nhận cột semantic role `feature`; cột `id`, `target`,
  `target_derived` không thể được đánh dấu cho selector.
- Learner view cũng loại ID/target/target-derived, nhưng có thể nhận metadata đã
  được protocol cho phép rõ ràng.
- Hai view giữ nguyên row order; selected indices chọn cùng enrollment trong
  learner view và row ID mapping riêng.

**Suy luận triển khai**

- Dùng `ColumnContract` machine-readable thay vì chỉ dựa trên danh sách tên cột.
  Các tên q/y/Qc/Yc/COELO/AFELO/ACELO/label còn có guard bổ sung để phát hiện gán
  sai semantic role.
- Runner ưu tiên `X_selector_train` khi artifact có ma trận này. Dataset lịch sử
  chưa có thì dùng `X_train` với diagnostic `selector_view=shared_legacy`; fallback
  này chỉ để tương thích/chẩn đoán, **không** được tính là G07 đạt cho CQ v1.
- Feature contract có hash và feature count riêng cho selector/learner trong
  diagnostics; không ghi dữ liệu hàng vào metadata public.

**Chưa hoàn tất**

- CQ v1 adapter chưa sinh `X_selector_*` và `feature_contract.json` vì schema dữ
  liệu tái tạo chưa được chốt. Do đó O17/G07 vẫn `IN_PROGRESS`.

**Bằng chứng cục bộ**

- `tests/test_feature_views.py`: loại ID/target-derived, bất biến khi hoán vị ID,
  giữ mapping indices sang learner view và từ chối semantic role sai.

**Bằng chứng dự kiến**

- `tests/test_method_fidelity.py`.
- Commit của lát metadata sau khi test đạt.

## Mẫu cho các mục tiếp theo

```text
Ngày / requirement IDs:
Xác nhận trực tiếp:
Suy luận triển khai:
File/symbol thay đổi:
Test/evidence:
Kết quả:
Điểm chưa đạt / blocker:
Ảnh hưởng claim:
```

