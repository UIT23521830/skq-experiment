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
- Learner view loại course ID/target/target-derived; mã người học, giảng viên và
  trường chỉ được nhận khi protocol cho phép rõ từng cột. Selector vẫn loại mọi ID.
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

### 14/10/2026 — Nền resource calibration đo thật

**Xác nhận trực tiếp đã áp dụng**

- Contract yêu cầu 50k/200k/800k dòng và ba replicate/mức; warm-up và
  steady-state là hai trường riêng.
- Mỗi observation gắn CPU/GPU/RAM/VRAM/thread/environment ID và giữ nguyên status.
- Fit log–log trên p90 từng cỡ, lưu slope/intercept/residual cùng point estimate và
  upper prediction bound tại kích thước Pool B.
- Trần selector mặc định 3 giờ. Vượt trần chỉ yêu cầu shared shard wrapper hoặc
  giải quyết protocol; `run_status` vẫn `null`. Chỉ phép chạy thật mới được ghi
  `timeout` bởi ResourceGuard.

**Suy luận triển khai**

- Không tự loại outlier; aggregation được ghi
  `p90_per_size_no_outlier_removal` để tránh che lần chạy chậm.
- Hệ số 1,96 dùng cho upper diagnostic trên log scale, chưa được diễn giải là CI
  thống kê của claim. Review chưa khóa goodness-of-fit threshold nên code không
  tự đặt ngưỡng R² để pass/fail.
- Thiếu size/replicate trả `needs_more_calibration`; tuyệt đối không dùng
  `estimated_operations` để bù cho phép đo thiếu.

**Chưa hoàn tất**

- Chưa có chín phép đo/selector trên đúng thiết bị Kaggle của CQ v1 và chưa tạo
  `resource_calibration.parquet`; QĐ16/G09 vẫn `IN_PROGRESS`.
- Shared shard wrapper phải được kiểm trên selector được M0 duyệt; wrapper không
  được tính là novelty.

**Bằng chứng cục bộ**

- `tests/test_resource_calibration.py`: đủ/thiếu replicate, upper bound và quyết
  định shard không tạo timeout dự báo.

### 14/10/2026 — CQ v1 enrollment, phase, Pool B và decision split

**Xác nhận trực tiếp đã áp dụng**

- Một dòng gốc là lượt ghi danh `(learner, course)`; q là trung bình LOQV qua các
  chương, y dùng ngưỡng 0,2/0,4 với chiều nhỏ là tốt.
- Nếu `euclid_to_111` có max lớn hơn 1 thì chia căn 3; audit ghi lại có thực hiện
  hay không. Quy tắc chương chưa mở là tham số bắt buộc, không có mặc định âm thầm.
- P1–P4 là 25/50/75/90% từ enroll_time tới course_end; nhãn enrollment cố định ở
  bốn snapshot.
- Pool B chỉ gồm P1–P4 của enrollment thuộc khóa train và có cột phase.
- Split temporal xếp `course_root_id` theo ngày mở đầu tiên; TEMPORAL và SGKF là
  hai quyết định loại trừ lẫn nhau.
- D09 kiểm cặp enrollment duy nhất, `y=tau(q)` và within-course label variation.

**Sửa lại suy luận ở lát selector view**

- Đọc lại QĐ3 xác nhận learner được giữ mã người học/giảng viên/trường theo cách
  TEMPO-DQ; chỉ course ID không làm feature. Contract đã đổi để cho phép ID theo
  từng cột ở learner, trong khi selector cấm mọi ID. Đây là correction được ghi
  công khai, không che thay đổi bằng cách sửa mô tả cũ mà không giải thích.

**Suy luận triển khai**

- Ngưỡng timestamp “đáng tin cậy” chưa được review chốt, vì vậy
  `max_timestamp_missing_rate` bắt buộc truyền vào `SplitDecisionThresholds`.
  Hai ngưỡng đã có trong review—ít nhất 10 khóa/lớp ở test và CI dev không quá
  0,005—được giữ làm mặc định nhưng vẫn cần giảng viên xác nhận tại M0.
- Hàm split/Pool B mới chỉ tạo contract và kiểm invariant, chưa tự dựng feature từ
  event log. Danh sách phép gộp sự kiện phải đến từ data card đã duyệt.

**Chưa hoàn tất**

- Chưa có CQ v1 thật, data card, `splits.json`, feature aggregation hay kiểm D01–D12
  trên dữ liệu; các gate liên quan vẫn `IN_PROGRESS_DATA_BLOCKED`.
- Chưa cài SGKF 5-fold × 2; chỉ có decision branch. Chỉ cài sau khi biết temporal
  có qua gate hay không, tránh chạy hai chiến lược nối tiếp.

**Bằng chứng cục bộ**

- `tests/test_cq_protocol.py`: chuẩn hóa LOQV, boundary nhãn, phase cutoff, split
  loại trừ, course-root grouping và Pool B bốn snapshot.

### 14/10/2026 — Endpoint hai cấp và prediction schema private

**Xác nhận trực tiếp đã áp dụng**

- UL là Macro-F1 cấp enrollment theo từng P1–P4; summary chính là trung bình bốn
  phase và P1 được giữ thành endpoint thứ cấp.
- Qc là mean qkc; Yc dùng cùng tau. EC chính là MAE của Q-hat theo PCC, chỉ tính
  cho khóa có `n_c >= n_min`; nếu phase không có khóa đủ điều kiện thì ghi `null`,
  không đổi thành 0.
- `mu_E,mu_G,mu_A` tính một lần từ enrollment của khóa train và bắt buộc thỏa
  `mu_E < mu_G < mu_A`.
- CC, signed error và course Macro-F1 được ghi là sensitivity, không thay PCC/EC.
- Prediction mức dòng có schema riêng và `row_level_visibility=private_only`.

**Suy luận triển khai**

- Chưa gắn course metrics vào runner lịch sử vì artifact cũ không có
  course_root/learner/q/phase đúng CQ v1. Tích hợp sớm sẽ tạo metric sai đơn vị.
- `n_min` không có mặc định trong hàm endpoint; config M0 phải truyền giá trị đã
  duyệt. Khi chưa đủ khóa, lý do thiếu được thể hiện bằng count và `null`.

**Chưa hoàn tất**

- Chưa khóa `n_min`, chưa có prediction CQ v1 và chưa kiểm Qc với data card sai số
  <1e-9. Vì vậy QĐ10–QĐ11/G04 vẫn `IN_PROGRESS`.

**Bằng chứng cục bộ**

- `tests/test_course_metrics.py`: schema private, UL/P1, PCC/EC, n_min và thứ tự mu.

### 14/10/2026 — Controls C01 và C03

**Xác nhận trực tiếp đã áp dụng**

- C01 lấy uniform random không hoàn lại, exact budget.
- C03 phân tầng `(phase, class)`, quota largest remainder và method weight
  `|P_g|/m_g`; test xác nhận mass từng tầng được bảo toàn trong sai số số thực.
- C01/C03 mang vai trò `control`, không phải phương pháp đề xuất và không claim
  tái hiện paper.
- C03 thiếu `phase_train` trả `blocked` kèm lý do; không fallback thành C02.

**Suy luận triển khai**

- `phase_train.npy` là artifact tách riêng thay vì nhét phase vào tọa độ feature.
  Runner chỉ truyền phase như metadata selector, còn learner/selector matrices giữ
  contract feature riêng.

**Chưa hoàn tất**

- CQ v1 adapter chưa sinh `phase_train.npy`; vì vậy C03 mới được xác nhận bằng toy
  contract, chưa có evidence D07 trên Pool B thật.

### 14/10/2026 — CoreTab-XGB OVA adapted

**Xác nhận trực tiếp đã áp dụng**

- Mỗi lớp chạy nhánh CoreTab-XGB binary class-vs-rest với seed `selector_seed+c`.
- Quota lớp dùng largest remainder theo prior Pool B; chỉ giữ positive rows tối đa
  quota. Union unique, không pad và thiếu thì `realized < requested`.
- Ledger diagnostics giữ quota, binary rows, positive rows, kept rows, seed,
  options và upstream commit cho từng lớp.
- Method mang nhãn chính xác `CoreTab-XGB (OVA, adapted)`; CoreTab native vẫn
  `binary_only` và multiclass trả `na_contract`.

**Suy luận triển khai**

- Options có một block chung và override theo lớp để ghi được tham số đã chốt.
  Code không tự thử nhiều cấu hình và không chọn theo test; tối đa ba cấu hình dev
  vẫn phải được khai báo ở protocol bên ngoài selector.
- Nếu một nhánh binary lỗi, wrapper giữ nguyên status của nhánh đó và dừng toàn
  method; không thay bằng random/proxy.

**Chưa hoàn tất**

- Chưa chạy toy reproduction của upstream checkout thật và chưa calibrate params
  để đủ positive quota trên dev CQ v1. Vì vậy QĐ14/G12 vẫn `IN_PROGRESS`.

**Bằng chứng cục bộ**

- `tests/test_coretab_ova.py`: quota, positive filtering, thiếu realized, seed và
  chặn binary contract.

### 14/10/2026 — Quy tắc headroom rho* trên dev

**Xác nhận trực tiếp đã áp dụng**

- Chỉ nhận UL dev của FullTrain-B và C02 tại rho 0,5/1/2/5%, đúng ba seed
  11/29/47; thiếu ratio/seed hoặc metric ngoài [0,1] bị chặn.
- Chọn rho lớn nhất có `UL(FullTrain-B)-mean(C02)>=0,01`; không mức nào đạt thì
  rho*=0,5%. Nếu rho* khác 5%, 5% được ghi secondary descriptive.
- Decision artifact tự khai báo `evidence_split=dev` và allowed inputs, không có
  tham số để truyền metric SKQ/baseline/test.

**Chưa hoàn tất**

- Chưa có 13 fit thật trên CQ v1 (1 FullTrain-B + 4×3 C02) nên QĐ12 vẫn
  `IN_PROGRESS`; code toy không được dùng để khóa rho*.

### 14/10/2026 — Paired course bootstrap và Holm

**Xác nhận trực tiếp đã áp dụng**

- Resampling theo `course_root_id`, 2.000 lần mặc định, alpha một phía 0,05; cùng
  course multiplicity được dùng cho mọi seed/phase trong một comparison.
- Dấu effect khóa rõ: `Delta_UL=UL(A)-UL(B)` và `Delta_EC=EC(B)-EC(A)`, dương đều
  có lợi cho A. Output gồm point estimate, CI hai phía, lower bound một phía, raw
  p và null boundary kể cả non-inferiority margin.
- Nếu course set giữa unit/method không khớp thì dừng; không tự inner-join/drop.
- Holm là hàm cho một family; caller phải gọi riêng K1–K5 và K1c–K5c.

**Suy luận triển khai**

- p-value bootstrap dùng hiệu chỉnh `(1 + count)/(B + 1)` để tránh p=0. Đây là
  lựa chọn triển khai chuẩn nhưng vẫn phải được ghi trong stats protocol freeze.
- Module chưa quyết định missing/failed run policy ngoài việc không drop course;
  policy rerun hạ tầng sau test vẫn cần giảng viên trả lời.

**Chưa hoàn tất**

- Chưa có run CQ v1 để tạo K1–K5/K1c–K5c, SD qua seed hoặc Holm report thật;
  QĐ6/G13 vẫn `IN_PROGRESS`.

**Bằng chứng cục bộ**

- `tests/test_statistics.py`: dấu UL/EC, deterministic bootstrap, mismatch course
  và Holm step-down.

### 14/10/2026 — Freeze manifest M1 schema v4

**Xác nhận trực tiếp đã áp dụng**

- Confirmatory chỉ được mở bằng manifest schema v4 ở trạng thái
  `M1_METHOD_FROZEN`; manifest khóa commit, config, fingerprint dữ liệu, split,
  feature schema, seed, rho*, learner params, class-weight policy, early stopping,
  shard policy, phương pháp thắng và protocol thống kê.
- Candidate list có từ một đến tối đa ba phương pháp. Candidate thắng phải có vai
  trò `proposed`, runnable và được registry cho phép confirmatory; candidate
  CoreTab-cell đang chờ duyệt vì vậy không thể được freeze.
- Manifest là bất biến: lệnh không overwrite file đang có. Mọi thay đổi sau M1
  phải tạo version/deviation riêng và liên kết `previous_manifest_id`.
- Runner confirmatory từ chối manifest V3 lịch sử. V3 chỉ còn dùng để đọc lại
  exploratory/historical run cũ.

**Suy luận triển khai**

- Dùng một file JSON `freeze-v4 --spec` để con người duyệt candidate/winner/hash
  trước khi chạy lệnh. CLI không tự đọc bảng metric để chọn winner, nhờ đó tránh
  tạo đường tuning ngầm sau khi nhìn test.
- Hash review được nhúng cố định theo hai tài liệu đầu vào. `manifest_id` là hash
  toàn bộ nội dung còn lại; sửa rho*, seed hoặc policy đều làm validation thất bại.
- `confirmatory_config_hash` được truyền từ config confirmatory đã chuẩn bị nhưng
  chưa chạy. Đây là suy luận nối hai trạng thái dev-freeze-confirmatory; nó không
  thay thế evidence lựa chọn trên dev.

**Chưa hoàn tất**

- Chưa thể tạo manifest M1 thật vì CQ v1, candidate được duyệt, rho*, learner
  params và selection evidence chưa tồn tại. File trong `docs` chỉ là schema/example,
  không phải freeze hợp lệ và không mở test.

**Bằng chứng cục bộ**

- `tests/test_freeze_v4.py`: round-trip, phát hiện tamper, chặn candidate chưa duyệt
  và chặn spec CLI thiếu trường.
- Lệnh dự kiến: `skq freeze-v4 --config <dev-config> --spec <approved-spec.json>`.

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

