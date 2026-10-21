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

### 14/10/2026 — Evidence Manifest và Claim Ledger G16

**Xác nhận trực tiếp đã áp dụng**

- Evidence có ID ổn định, requirement IDs, commit, config/split hash, run IDs,
  artifact SHA-256, visibility, producer command và status. Evidence đã ghi không
  được overwrite.
- Claim empirical phải trỏ tới ô bảng/hình, khóa dòng trong `runs_long`, run IDs,
  provenance và evidence IDs; một file nhận xét thủ công không đủ làm evidence.
- Claim `supported` chỉ hợp lệ khi mọi evidence có status `pass` và bao phủ toàn
  bộ run ID của claim. Audit giữ riêng từng finding, không gộp hoặc che lỗi.
- Manifest public chỉ ghi label và SHA-256; đường dẫn/nội dung artifact mức dòng
  không được chép vào ledger public.

**Suy luận triển khai**

- Mỗi claim là một JSON bất biến thay vì một bảng duy nhất có thể bị sửa âm thầm.
  `record_id` hash toàn nội dung và audit lại semantic gate, kể cả record được tạo
  ngoài API.
- Cho phép evidence trạng thái `fail`, `blocked`, `partial`, `not_run` để lưu đúng
  thất bại; các trạng thái này không thể nâng claim thành `supported`.
- Tool audit không đọc nội dung artifact private, chỉ xác minh manifest, liên kết
  evidence và hash đã khai báo. Đây là lựa chọn giảm nguy cơ rò dữ liệu.

**Chưa hoàn tất**

- Chưa có evidence/run CQ v1 thật và chưa tạo claim kết quả nào. Hai file example
  chỉ mô tả schema, không phải bằng chứng.
- Aggregate runner chưa tự phát hành evidence; bước nối tự động chỉ thực hiện sau
  khi schema CQ v1 và danh sách endpoint M0 được khóa.

**Bằng chứng cục bộ**

- `tests/test_evidence_ledger.py`: bất biến, không lộ path private, bao phủ run,
  evidence status và phát hiện record bị sửa.
- `scripts/audit_claim_ledger.py --artifact-root <root>` trả exit code khác 0 khi
  có finding.

### 14/10/2026 — State machine M0 kế thừa M1

**Xác nhận trực tiếp đã áp dụng**

- M0 khóa split/hash, rho*, class-weight policy, learner params, `n_min`,
  `delta_c`, shard/resource rule, tối đa ba candidate, seed và feature schema khi
  test còn khóa và trước dev selection.
- M1 bắt buộc đọc M0 hợp lệ, liên kết bằng `previous_manifest_id` và không được
  thay candidate list, rho*, shard policy, seed, feature/split/data hash hoặc
  learner policy đã khóa ở M0.
- Config M0 phải có `evidence_role=dev_selection`; config confirmatory không thể
  được dùng để tạo M0. M1 thiếu M0 bị dừng trước khi tạo artifact.

**Suy luận triển khai**

- M0 và M1 là hai file bất biến riêng. Việc tách file giúp kiểm toán đúng chuyển
  trạng thái, thay vì dùng một file rồi sửa `state` tại chỗ.
- Candidate M0 phải có role `proposed`, status `implemented` và
  `confirmatory_allowed=true` trong registry. Candidate CoreTab-cell đang chờ
  duyệt không thỏa điều kiện này, nên contract không cho lách bằng spec JSON.
- M0 khóa commit; nếu code thay đổi giữa M0 và M1 thì phải tạo lại protocol/deviation
  theo phê duyệt, không tiếp tục bằng manifest cũ.

**Chưa hoàn tất**

- Chưa tạo M0 thật vì thiếu CQ v1, data card, phép đo tài nguyên, headroom,
  learner winner và candidate được duyệt. File spec example không phải evidence.

**Bằng chứng cục bộ**

- `tests/test_freeze_v4.py`: M0/M1 round-trip, tamper detection, role config,
  candidate approval, thiếu M0 và CLI spec.
- Lệnh dự kiến: `skq freeze-m0-v4 --config <dev-config> --spec <m0-spec.json>`.

### 14/10/2026 — Môi trường Kaggle Free GPU T4 và cách tính tài nguyên

**Xác nhận trực tiếp đã áp dụng**

- Review yêu cầu kiểm kê `nvidia-smi`, CPU, RAM, VRAM, dung lượng, Python,
  CUDA/thư viện, giới hạn phiên và số giờ khả dụng; không chỉ ghi “Kaggle T4”.
- Mỗi run báo cả wall-clock và GPU-giờ cấp phát bằng wall-clock giờ nhân số GPU
  được cấp; mức sử dụng GPU chỉ là diagnostic, không dùng để giảm GPU-giờ.
- QĐ16 vẫn dùng ba cỡ 50k/200k/800k, ba replicate, trần selector ba giờ và giữ
  status của từng phép đo riêng.

**Lựa chọn môi trường của nhóm**

- Nền chính được chọn là Kaggle Free với accelerator T4. Script kiểm tên GPU
  thực tế của từng phiên và ghi số GPU được cấp; không hard-code T4 x2 vì số thiết
  bị có thể khác giữa phiên dù lần chạy cũ đã thấy hai thiết bị CUDA.

**Suy luận triển khai**

- Nếu GPU không phải T4 hoặc không được cấp, environment manifest trả
  `blocked_gpu_mismatch`; lỗi `nvidia-smi`, `lscpu`, `free` và `df` được giữ thành
  từng command status, không gộp thành “môi trường lỗi”.
- `environment_id` hash phần cứng/phần mềm/policy/giới hạn khai báo. Calibration
  của một selector chỉ fit khi mọi observation cùng environment ID.

**Chưa hoàn tất**

- Chưa chạy cell kiểm kê trên phiên Kaggle cuối cùng, nên chưa có con số CPU,
  RAM, VRAM, giới hạn phiên và giờ khả dụng thực tế. Đây vẫn là evidence bắt buộc
  trước G09/M0.

**Bằng chứng cục bộ**

- `scripts/capture_kaggle_environment.py` và `tests/test_environment_manifest.py`.
- `tests/test_resource_calibration.py` kiểm wall-clock/GPU-hour và calibration.

### 14/10/2026 — Quality Gate Ledger G00 đến G16

**Xác nhận trực tiếp đã áp dụng**

- Mỗi gate có phase, điều kiện đạt, loại evidence và hành động khi fail riêng.
- Audit luôn xuất đủ gate, kể cả gate chưa chạy; thiếu evidence không được xem là
  pass. `missing_evidence`, `invalid_evidence`, `failed`, `blocked` và `incomplete`
  là các trạng thái khác nhau.
- Overall chỉ pass khi toàn bộ gate trong spec đều pass; không lấy trung bình và
  không để gate mạnh che gate thất bại.

**Suy luận triển khai**

- Mapping gate → evidence ID là input được duyệt riêng. Auditor không tự đoán
  evidence từ tên file, tránh gắn nhầm một pytest log cho nhiều yêu cầu.
- Gate ledger có `audit_id` hash nội dung và được ghi không overwrite.

**Chưa hoàn tất**

- Chưa có evidence map thật nên hệ thống hiện phải báo `not_ready`, phù hợp trạng
  thái nền đang chờ CQ v1 và các phép đo Kaggle.

**Bằng chứng cục bộ**

- `docs/quality_gates_v2.json`, `scripts/audit_quality_gates.py` và
  `tests/test_quality_gates.py`.

### 14/10/2026 — Kiểm tra hồi quy cuối phần nền V2

**Kết quả kiểm chứng**

- Toàn bộ 137 test của repo đạt ở lần kiểm tra cuối, gồm test pipeline lịch sử
  và contract V2 mới.
- `compileall` đạt cho `src` và `scripts`; toàn bộ file `.py`, `.md`, `.json`
  trong source/docs/config/tests đọc được bằng UTF-8 strict.
- Quality-gate audit với evidence map rỗng trả `not_ready` và đúng 17 trạng thái
  `missing_evidence`; không có gate nào pass giả.
- Privacy audit cuối có 0 finding ở tracked files, 3 finding lịch sử của workbook
  `MA_TRAN_THUC_NGHIEM_SKQ_FULL.xlsx`, 0 finding archive. G01 vẫn
  `BLOCKED_REMEDIATION`; kết quả này không bị ghi thành pass.
- Fixture kiểm scanner credential được ghép chuỗi tại runtime để chính source test
  không giống credential thật; test vẫn xác nhận scanner phát hiện mẫu và không
  chép giá trị bí mật vào finding.

**Phạm vi kết luận**

- Nền code V2 đã có contract cho dữ liệu/split/view/label, trọng số, learner,
  tài nguyên, control, CoreTab OVA, thống kê, M0/M1, evidence/claim và gate audit.
- Chưa có CQ v1, phép đo Kaggle T4, baseline fidelity đầy đủ, candidate SKQ-PC
  được duyệt hoặc manifest M0 thật. Vì vậy chưa được chạy confirmatory và chưa có
  claim kết quả mới; đây là blocker đúng thiết kế, không phải test code thất bại.

**Bằng chứng dự kiến**

- `tests/test_method_fidelity.py`.
- Commit của lát metadata sau khi test đạt.

### 14–16/10/2026 — Baseline fidelity G10 theo Review 12 §7.6/§7.11

**Xác nhận trực tiếp đã áp dụng**

- Panel bổ sung C01, C03, Moderate-DS, CCS, Data-OOB và Kernel Thinning;
  đồng thời kiểm cùng Gonzalez, CoreTab-XGB OVA và BDIS đang dùng trong bảng.
- Mỗi source ngoài được khóa URL và full commit. Source/dependency lỗi giữ
  `blocked`/`failed` trong mẫu số, tuyệt đối không fallback sang proxy.
- Moderate-DS được ghi adapted vì thay image embedding bằng `selector_view`
  chuẩn hóa. CCS được ghi adapted vì EL2N đến từ OOF-XGBoost. Kernel Thinning
  được ghi adapted vì quota theo lớp và deterministic pre-pool. CoreTab OVA giữ
  nhãn adapted/no-pad theo QĐ14.
- Data-OOB giữ nguyên estimator `RandomForestClassifierDV` và OOB value từ
  source, nhưng việc stable top-k value để tạo exact-budget subset được khai báo
  là adaptation của protocol, không gọi là native nguyên trạng.

**Suy luận triển khai**

- G10 được tách thành manifest cấu trúc và evidence toy thực. Manifest không có
  trường tự khai `passed`; strict audit chỉ pass khi evidence có đủ 10 status
  `success`.
- Toy artifact không lưu index/trọng số/dòng dữ liệu. Đây là kiểm interface và
  provenance, không phải kết quả CQ v1 hoặc bằng chứng hiệu quả.
- GoodPoints được pin commit ở cả lock và dependency. Checkout dùng sparse path
  `goodpoints`; package cần build Cython trên Linux/Kaggle.

**Kết quả local và Kaggle T4**

- Structural audit đạt 10/10 method rows.
- Toy local đạt 8/10: C01, C02, C03, Gonzalez, Moderate-DS, CCS, Data-OOB và
  CoreTab-XGB OVA đều success.
- Kernel Thinning bị `blocked` vì Python local chưa build GoodPoints/Cython;
  BDIS bị `blocked` vì local thiếu `faiss-cpu`. Không phương pháp nào bị đổi tên
  hoặc thay proxy trong lượt local.
- Lượt Kaggle T4 đầu ở commit `810fa453085c389a969727d6271b2a210f3e7045`
  đạt 9/10; GoodPoints bị `blocked` vì checkout source chưa build che package
  Cython runtime. Đây là lỗi tích hợp/import, không phải lỗi thuật toán. Adapter
  được sửa để checkout chỉ kiểm URL/commit, còn runtime import package đã build
  và xác minh `direct_url.json`; không thay Kernel Thinning và không dùng proxy.
- Lượt rerun Kaggle Free T4 ở commit
  `fb4bd97a47f1c897b029199a4648b9b39d9d0317` đạt **10/10 success**, strict
  audit `passed`, `findings=[]`. Môi trường ghi nhận hai Tesla T4, CUDA sẵn sàng,
  Python 3.13.15. GoodPoints runtime là distribution 0.6.3 từ URL chính thức và
  full commit `181b12ade5dd02a61b65ed5cb9444c916fa3135f`.
- BDIS chạy source chính thức thành công nhưng trả 68/120 dòng theo contract
  `native_realized`. G10 chỉ xác nhận fidelity/interface; tỷ lệ realized này phải
  tiếp tục được báo cáo, không được mô tả như so sánh exact-budget 120 dòng.
- G10 hiện **PASS**. Kết quả toy 600 dòng, 12 feature, 3 lớp, budget 20% không
  phải số liệu CQ v1 và không chứng minh phương pháp nào tốt hơn.

**Bằng chứng code**

- `docs/method_fidelity_v2.json`, `external/official_repos.lock.json`.
- `scripts/run_method_fidelity_toys.py`, `scripts/audit_method_fidelity.py`.
- `tests/test_modern_baselines.py`, `tests/test_fidelity_audit.py`.
- `docs/evidence/manifests/EV-G10-FIDELITY-001.json`: manifest public chỉ chứa
  provenance và SHA-256. Archive private có SHA-256
  `4fae924fd14f2a0032ba03ccdb007bf5a1ad6fcf8984bb180417a1bb3c5ab0e5`;
  không commit archive hoặc artifact mức dòng vào Git.

### 14/10/2026 — G00 config audit và missing/failed-run policy G13

**Xác nhận trực tiếp đã áp dụng**

- Confirmatory config từ chối synthetic, method không được phép confirmatory và
  method không mang evidence role phù hợp. Dev selection từ chối quá ba candidate
  proposed hoặc candidate chưa được review/registry duyệt.
- Mẫu số thống kê là toàn bộ ô method × selector seed × phase đã preregister.
  Run failed/timeout/blocked không bị drop và metric lỗi không được impute bằng 0.
- Nếu thiếu, trùng hoặc có ô non-success, hypothesis liên quan được ghi
  `not_estimable_incomplete`; bảng mô tả vẫn báo completion/failure rate.

**Suy luận triển khai**

- Review yêu cầu không bỏ run lỗi khỏi mẫu số nhưng chưa chỉ định phép gán metric
  cho lỗi. Chọn không impute và không suy luận khi panel chưa đủ là phương án bảo
  thủ, tránh vừa thưởng vừa phạt tùy ý; cần khóa cùng protocol tại M0.
- `statistics_protocol_v2.json` khóa dấu effect, alpha 0,05 một phía, 2.000
  bootstrap theo course root, hai Holm family và missing policy. Đây là protocol
  nền, chưa phải hash M0 thật.

**Chưa hoàn tất**

- Chưa có expected-cell manifest và run CQ v1 thật, nên G13 chưa thể pass ở mức
  evidence. Quyết định có cho rerun lỗi hạ tầng sau test hay không vẫn cần giảng
  viên xác nhận; mọi rerun nếu được phép phải ghi deviation và giữ lần lỗi đầu.

**Bằng chứng code**

- `src/skq_exp/training/completeness.py`,
  `scripts/audit_statistics_readiness.py`, `docs/statistics_protocol_v2.json`.
- `tests/test_completeness.py`, các test G00 trong `tests/test_config.py`.

### 17/10/2026 — Nền bốn biến thể SKQ-PC trước khi chạy CQ v1

**Xác nhận trực tiếp đã áp dụng**

- Ba candidate đã được Review 12 nêu rõ được hiện thực riêng: `SKQ-PC`,
  `SKQ-PC + LRQ-SQ` và `SKQ-PC-R`. Cả ba dùng Pool B, exact budget, tầng
  `phase × class`, Gonzalez/Voronoi cell, RFF và simplex-QP; LRQ chỉ dùng OOF-LR
  train-only, còn bản R chỉ thay herding bằng random trong cell.
- Candidate chuẩn và các biến thể không tái sử dụng tên P01–P11 lịch sử. Mã mới
  nằm ở `src/skq_exp/methods/proposed/skq_pc.py` để contract có thể kiểm toán.

**Suy luận triển khai / deviation chờ duyệt**

- Theo yêu cầu nội bộ ngày 17/10, nhóm giữ thêm candidate thứ tư
  `SKQ-PC/CoreTab-cell`. Candidate này thay Gonzalez cell bằng leaf signature
  CoreTab-XGB nhưng giữ tầng `phase × class`, herding và QP. Nó không phải
  CoreTab native và chưa được review phê duyệt.
- Candidate thứ tư mang role `experimental_candidate`, evidence role
  `exploratory`, `confirmatory_allowed=false`. Config chỉ chấp nhận khi
  `evidence_role=dev_selection`, `test_locked=true` và khai báo rõ
  `pending_approval_acknowledged=true`. Freeze M0/M1 và confirmatory config vẫn
  từ chối candidate này. Vì vậy code có thể chạy thăm dò dev nhưng chưa tạo claim.
- Số cell khả thi trong mỗi tầng được khóa là
  `min(128, quota tầng, population tầng)`. Với CoreTab, nếu số leaf lớn hơn quota,
  các leaf nhỏ được gộp vào residual cell xác định. Đây là quy tắc triển khai cần
  xin giảng viên xác nhận cùng việc cho phép candidate thứ tư.

**Test/evidence**

- `tests/test_skq_pc.py` kiểm exact budget, unique row, tám tầng khả dĩ của CQ v1
  binary bốn phase, bảo toàn mass tầng, tính tái lập và dev-only gate.
- Nhóm test tích hợp `test_skq_pc`, `test_method_fidelity`, `test_config`,
  `test_freeze_v4`, `test_selectors`, `test_resources`, `test_full_panel` đạt
  53/53 trên local. Đây là evidence nền code, chưa phải kết quả utility CQ v1.

**Điểm chưa đạt / blocker**

- Chưa có xác nhận của giảng viên cho candidate thứ tư; không được đưa vào M0/M1.
- CQ v1 binary mới chưa có adapter/fingerprint/split manifest trong repo tại thời
  điểm triển khai này, vì vậy chưa có run dev thật và chưa kết luận hiệu quả.

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

### 20/10/2026 — Tích hợp CQ v1 `phase_features_v2` ở chế độ development-only

**Căn cứ xác nhận trực tiếp từ Review 12–13:** Pool B dùng đủ P1–P4 của train;
selector SKQ-PC phân tầng phase × class; chọn candidate chỉ trên dev; test không
được dùng để tune; tối đa ba candidate A/B/C; ID/target/target-derived không làm
tọa độ selector.

**Đã thực hiện:**

- Đăng ký `course_quality_v1` với nhãn chính `y_alpha_1`; đăng ký riêng
  `course_quality_v1_afelo0p1` cho sensitivity, không trộn hai định nghĩa nhãn.
- Adapter đọc snapshot Parquet đã qua các validation của nhóm dữ liệu, tạo Pool B
  994.608 dòng từ bốn phase train và giữ phase dưới dạng metadata cho C03/SKQ-PC.
- Hai view hiện dùng cùng 56 feature số; loại `phase_fraction`, năm mã categorical,
  `user_id`, `course_id`, mọi q/y và metadata khỏi hình học. Selected index vẫn
  tham chiếu đúng row order của learner matrix.
- Dev được đánh giá riêng P1, P2, P3, P4; config smoke có 6 method × 1 XGBoost ×
  4 phase = 24 evaluation rows. Test vẫn `test_locked=true`.
- Config development đầu tiên dùng đúng ba candidate Review nêu: `skq_pc`,
  `skq_pc_lrq_sq`, `skq_pc_r`; thêm FullTrain-B, C02 và C03 làm đối chứng kỹ thuật.
- Toàn bộ 148 test hiện tại và smoke thật C03 → LR → dev P1–P4 đều PASS.

**Suy luận triển khai cần được báo rõ:** snapshot hiện chỉ có `course_id`, chưa có
`course_root_id`. Adapter dùng hash `course_id` để audit split tạm thời và tự ghi
`confirmatory_eligible=false`. Vì vậy run hiện tại chỉ kiểm tra tích hợp/dev, không
được dùng để freeze M0/M1, mở test hay đưa ra claim xác nhận. Cần nhóm dữ liệu bổ
sung ánh xạ `course_id -> course_root_id` trước confirmatory/bootstrap theo review.

**Deviation preprocessing:** adapter tái sử dụng preprocessing train-only theo
từng phase do snapshot cung cấp và ghi hash đầy đủ; chưa tự fit lại một scaler trên
Pool B. Nếu giảng viên yêu cầu một preprocessing chung cho pooled phases thì phải
đăng deviation, tạo adapter version mới và chạy lại dev — không sửa đè evidence.

### 21/10/2026 — Screening CQ v1 ở rho=2% và chuẩn hóa evidence pipeline

**Evidence thực nghiệm hiện có**

- Archive private `skq_cq_v1_screening_rho2pct_seed11_29_47_v1.tar.gz` chạy ở
  commit `46f733a55f754b699656a0e69c1e24911d79891d`, Kaggle T4, test khóa.
- Panel gồm FullTrain, C02, C03, SKQ-PC, SKQ-PC + LRQ-SQ và SKQ-PC-R; XGBoost,
  model seed 42, selector seed 11/29/47, bốn dev phase. Cả 64/64 evaluation rows
  thành công; không có method error.
- Pool B có 994.608 dòng; budget 2% là 19.892 dòng, xấp xỉ nén 50 lần. Một model
  được fit trên coreset rồi tái sử dụng để đánh giá riêng trên bốn dev phase.
- `EV-CQ-SCREEN-RHO2-001` chứa 64 run_id, config hash, split hash và SHA-256 của
  archive cùng các bảng overall/per-label/confusion/ledger. Manifest public không
  chứa đường dẫn dữ liệu riêng hay dữ liệu mức dòng.

**Kết quả development, chưa phải confirmatory**

- FullTrain: Macro-F1 0,5802; MCC 0,5834; balanced accuracy 0,7030; worst-class
  recall 0,5268; PR-AUC macro 0,6862; log loss 0,5243.
- C02: 0,5649 / 0,5588 / 0,6405 / 0,3630 / 0,6617 / 0,5399.
- C03: 0,5862 / 0,5869 / 0,6302 / 0,2943 / 0,6595 / 0,5049.
- SKQ-PC: 0,5552 / 0,5679 / 0,6273 / 0,3150 / 0,6772 / 0,5501.
- SKQ-PC + LRQ-SQ: 0,5860 / 0,6070 / 0,6258 / 0,2599 / 0,6537 / 0,4878.
- SKQ-PC-R: 0,5785 / 0,5813 / 0,6189 / 0,2698 / 0,6766 / 0,5150.
- Thứ tự sáu số trên là Macro-F1 / MCC / balanced accuracy / worst-class recall /
  PR-AUC macro / log loss. LRQ-SQ hiện mạnh nhất về MCC và log loss, gần C03 về
  Macro-F1, nhưng kém rõ về recall lớp 0. Vì vậy chưa được phép claim vượt trội.

**Quyết định tạm thời**

- Giữ LRQ-SQ làm candidate chính để kiểm tra tiếp; giữ SKQ-PC và SKQ-PC-R làm
  ablation. C03 vẫn là đối chứng bắt buộc vì đạt Macro-F1 tốt nhất trong panel.
- Chưa mở test, chưa freeze M1, chưa chạy phép kiểm định confirmatory. Snapshot
  thiếu `course_root_id`, nên bootstrap theo course root và xác nhận không rò rỉ
  giữa các phiên bản cùng khóa học chưa thể thực hiện đúng review.

**Sửa nền evidence sau screening**

- SKQ-PC ghi rõ `qp_converged`, `qp_constraint_valid`, sai số tổng trọng số, trọng
  số nhỏ nhất, solver/iterations theo từng tầng và tổng hợp ở cấp method.
- FullTrain/C02/C03/SKQ-PC ghi `passes_over_train`, loại phép đo và định nghĩa;
  selector chưa khai báo được đánh dấu `unknown`, không tự suy diễn thành 0.
- Temporal evaluator ghi rõ selection dùng chung cho bốn split, selection cost
  không được cộng bốn lần, thời gian đánh giá tăng thêm theo split, và VRAM bằng
  0 trên CPU được đổi thành `not_measured` thay vì báo 0 MB.
- 148/148 test qua khi pytest dùng thư mục tạm trong workspace; nhóm test trực
  tiếp về SKQ-PC/temporal/selectors đạt 18/18.

**Điểm chờ xác nhận / dữ liệu**

- Cần `course_root_id` thật hoặc xác nhận bằng văn bản rằng `course_id` đã là khóa
  gốc bất biến; nếu không, toàn bộ kết quả trên chỉ là development evidence.
- Cần giảng viên duyệt candidate cuối và ba ablation tối thiểu trước khi tạo M0.
- Cần xử lý hoặc được duyệt ngoại lệ cho ba object XLSX còn trong Git history.

