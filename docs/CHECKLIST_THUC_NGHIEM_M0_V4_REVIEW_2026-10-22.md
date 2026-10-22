# Checklist thực nghiệm M0 V4 theo Review ngày 22 tháng 10 năm 2026

**Mục đích:** theo dõi toàn bộ việc bên thực nghiệm phải sửa và phải chạy để nộp
điểm kiểm tra M0-V4 ngày 29/10/2026, đồng thời làm bảng đối chiếu gửi giảng viên.

**Kết luận hiện tại:** hạ tầng code cốt lõi theo Review 22/10 đã được bổ sung;
gói CQ V4 dev-only đã nhận, kiểm hash và ingest thành công. M0-V4 vẫn chưa hoàn
thành vì chưa chạy FullTrain, headroom và QĐ16 trên V4. Test V4 tiếp tục khóa đến
khi giảng viên duyệt freeze manifest tại M1 ngày 08/11/2026.

**Nhánh làm việc:** `cq-v1-protocol-fixes`
**HEAD nền của lô sửa:** `82c878a59c48689c45350b34c8f3ee92fc11b082`
**Trạng thái phát hành:** xem commit mới nhất trên nhánh làm việc; chưa mở PR.

## 1. Quy ước trạng thái

- [x] Đã hoàn thành và có code/test hoặc artifact kiểm chứng.
- [ ] Chưa hoàn thành.
- **PARTIAL:** đã có hạ tầng nhưng còn thiếu dữ liệu hoặc chưa chạy bằng chứng.
- **BLOCKED-DATA:** chỉ có thể chạy sau khi nhận CQ V4 đạt contract.
- **DEFERRED-M1:** cố ý để sau điểm kiểm tra 29/10 theo Review.
- **LOCKED:** không được thực hiện ở M0-V4.

## 2. Bảng kiểm tổng hợp theo yêu cầu giảng viên

| ID review | Yêu cầu phải đáp ứng | Phần code/hạ tầng đã làm | Bằng chứng còn phải tạo | Trạng thái | Hạn |
| :-- | :-- | :-- | :-- | :-- | :-- |
| QĐ18 | Chỉ làm train/dev đến M1; test V4 chỉ mở sau freeze | Adapter V4 từ chối mọi file test; config M0 đều `test_locked=true` | Bundle dev-only đã xác nhận không có test; tiếp tục kiểm archive notebook | **READY-TO-RUN** | 29/10 |
| QĐ19, R3 | Tạo `course_family_id` bằng connected components Jaccard ccid 0,9, tối thiểu 5 ccid; sensitivity 0,8 | Code protocol và dữ liệu thực đều có; 1.740 family/1.808 course, báo cáo 0,8 đi kèm | Đưa thống kê và hash vào báo cáo M0 | **ĐÃ NHẬN DỮ LIỆU** | 24–26/10 |
| QĐ19 | Test là 20% family mở muộn nhất; phần còn lại train/dev 70:10, seed 42, stratify quartile cỡ × `has_E` | Bundle có `splits.json`, `family_splits.parquet`, `course_splits.parquet`; adapter xác nhận train–dev family overlap = 0 | Đưa audit/hash vào báo cáo M0 | **ĐÃ NHẬN DỮ LIỆU** | 24–26/10 |
| QĐ19 | Fit preprocessing lại chỉ trên train V4; giữ hai feature view | Bundle có 56 feature selector và 62 feature learner; adapter kiểm finite/subset và không tự fit lại | Ghi hash preprocessing/feature lists trong archive chạy | **READY-TO-RUN** | 26/10 |
| O20 | Báo concentration và bootstrap theo family | Data card đã có largest share/effective course; bootstrap nhận `resampling_unit=course_family_id` | Chạy CI 2.000 family-bootstrap cho các contrast mô hình | **PARTIAL / READY-TO-RUN** | 29/10 |
| QĐ20, O21 | Ứng viên thứ ba là SKQ-PC-√, quota tỷ lệ căn bậc hai, floor 20 | Đã đăng ký `skq_pc_sqrt`; exact bounded sqrt allocation; kết quả unit contract trên số V3 là E/G/A = 35/221/386 mỗi phase | Chạy ba candidate trên dev V4 tại rho* và báo per-class | **PARTIAL** | 29/10 hạ tầng; 06/11 panel |
| QĐ20 | SKQ-PC-R chuyển thành ablation A3 | Registry đổi role thành `ablation`, evidence `appendix`; không còn trong danh sách calibration candidate | Chạy A3 ở giai đoạn ablation sau khi chốt winner | **DEFERRED-M1** | 30/10–06/11 |
| QĐ20 | C03 chính dùng cùng allocation với winner; C03 tỷ lệ chỉ báo mô tả | C03 nhận `allocation_policy` và `allocation_floor`; cùng gọi một allocator với SKQ-PC-√ | Sau khi chọn winner, khóa config C03 cùng quota; chạy thêm C03 proportional | **PARTIAL** | 30/10–06/11 |
| QĐ20 | A2 dùng cùng allocation với winner | Allocator dùng chung đã có | Nối option vào config A2 sau khi winner được chốt | **CHƯA LÀM** | 30/10–06/11 |
| QĐ21 | Main dùng natural class weight; balanced chỉ sensitivity; target `y_alpha_1` | Config và bundle V4 khóa `y_alpha_1`; main dùng natural | Chạy balanced sensitivity riêng, không trộn bảng chính | **READY-TO-RUN** | 29/10 |
| QĐ21 | `nmin=30`, `delta_C=0,01`, `delta=0,005`; EC và signed deviation là endpoint course | Data card có 67 course dev đủ `nc>=30`, ICC và oracle floor; predictions giờ giữ course/family ID | Chạy mô hình và báo EC/signed deviation thực | **READY-TO-RUN** | 29/10 |
| QĐ21, QĐ12 | Headroom V4 tại 0,5/1/2/5%, C02 5 seed 11/29/47/71/101 | Đã có 4 config V4 5 seed và `compute_cq_v4_headroom.py`; output ghi SD/SE input seed | Chạy 20 selection-seed cells × 4 dev phase; tính rho* và CI family-bootstrap | **READY-TO-RUN** | 26–29/10 |
| QĐ22, O23 | FullTrain-A là snapshot lambda=1 đúng cohort train V4, không phải P4 | Bundle có 131.906 dòng FullTrain-A; adapter xác nhận cohort A=B; runner đánh giá dev P1–P4 | Chạy XGB natural và báo cạnh FullTrain-B | **READY-TO-RUN** | 26–29/10 |
| QĐ22, O22 | Kernel Thinning phải là classwise Compress++; nếu sau shard vẫn >3 giờ thì TIMEOUT | Đã thay KT trực tiếp bằng classwise shard → upstream `compresspp_kt` → KT exact; diagnostics ghi upstream, shard, candidate, prepool, timeout 10.800 s | Chạy fidelity G10; chạy lại QĐ16; lưu checkpoint/time/RSS; nếu >3 giờ ghi TIMEOUT | **PARTIAL** | 26–29/10 |
| QĐ23 | Repo public, không rewrite history; không commit dữ liệu/prediction dòng | Nhánh hạ tầng đã push; dữ liệu, ZIP và processed arrays vẫn untracked/ignored | Sửa nốt tài liệu ghi private; kiểm allowlist ở mọi commit sau | **PARTIAL** | 24/10 |
| O24 | Data card nêu căn cứ/phiên bản nhãn và khác biệt với LoDiBi/TEMPO-DQ | Đã nhận Data Card V4, formula policy, feature dictionary và mô tả P95/sentiment/NULL/chapter -1 | Xin giảng viên duyệt deviation không đối chiếu TEMPO-DQ và human review 20 cặp | **PARTIAL / CHỜ DUYỆT** | 29/10 |
| Y17 | `references.bib` đủ tài liệu và DOI | Chưa thuộc lô sửa code này | Bổ sung 21 tài liệu và tài liệu Neyman 1934; chạy kiểm tra citation | **CHƯA LÀM** | 29/10 |
| Y18 | Sửa mọi tài liệu ghi repo private | Chưa sửa toàn bộ | Tìm toàn repo và sửa theo QĐ23 | **CHƯA LÀM** | 24/10 |
| Y19 | Hợp nhánh vào main, không squash; tạo tag `review-2026-10-22` | Nhánh `cq-v1-protocol-fixes` đã có commit hạ tầng và được push | Mở PR, merge commit vào main và tạo tag sau khi evidence V4 đạt | **PARTIAL** | 24–29/10 |
| Y20 | Thống nhất tên V1, V3, V4 trong archive/manifest | Code mới dùng `course_quality_v4` và `CQ V4` | Kiểm tên mọi notebook/archive/report mới | **PARTIAL** | 24/10 |
| Y21 | Tinh chỉnh LR theo lưới 8 cấu hình, vẫn không hội tụ thì ghi descriptive | Config V4 hiện mới khóa XGB cho M0 headroom | Tạo config LR grid, chạy FullTrain-A/B dev, lưu convergence diagnostics | **CHƯA LÀM** | 29/10 |
| Y22 | Headroom phải có mean, SD, SE, số seed | Hàm headroom giữ toàn bộ seed values; script V4 khóa 5 seed | Bổ sung bảng xuất cuối cùng có SD, SE, Delta, CI half-width và cờ đạt | **PARTIAL** | 29/10 |
| Phụ lục B | Có `cq_patch_1022.py` và `test_cq_patch_1022.py` 6/6 | Đã tạo API tương thích và đúng 6 contract test | Đưa kết quả pytest vào báo cáo/PR | **ĐÃ LÀM** | 24–26/10 |

## 3. Các sửa đổi code đã hoàn thành trong lô hiện tại

- [x] Thêm exact allocator `sqrt_floor` với floor/cap và lỗi rõ khi budget bất khả thi.
- [x] Thêm candidate `skq_pc_sqrt` vào registry và factory.
- [x] Đổi `skq_pc_r` từ candidate sang ablation A3/appendix.
- [x] Cho C03 nhận cùng allocation policy/floor với candidate chốt.
- [x] Thay danh sách ba candidate QĐ16 thành `skq_pc`, `skq_pc_lrq_sq`, `skq_pc_sqrt`.
- [x] Thay wrapper Kernel Thinning bậc hai bằng classwise sharded Compress++ và KT exact.
- [x] Ghi diagnostics cho Kernel Thinning: upstream function/commit, shard, candidate rows,
  final prepool, rounds, bandwidth, timeout contract và CPU device.
- [x] Thêm family builder, family split, temporal overlap và concentration V4.
- [x] Cho bootstrap ghi đúng đơn vị `course_family_id`.
- [x] Đăng ký dataset `course_quality_v4` và adapter dev-only.
- [x] Adapter từ chối test file, cấm ID/target trong feature, kiểm family leakage,
  kiểm FullTrain-A cùng cohort với Pool B và không fit lại preprocessing.
- [x] Thêm evaluator `c00_full_train_a`; một model A được dùng lại cho dev P1–P4.
- [x] Thêm config FullTrain-A, FullTrain-B và bốn mức headroom V4 5 seed.
- [x] Thêm script tính headroom V4 tách khỏi headroom lịch sử V1 ba seed.
- [x] Thêm `cq_patch_1022.py` và đúng sáu test yêu cầu.
- [x] Kiểm tra cấu hình: cả 6 config V4 đọc và validate thành công.
- [x] Kiểm thử tập trung: 62/62 test liên quan Review 22/10 chạy đạt cục bộ.
- [x] Regression toàn repo: 195/195 test chạy đạt sau tích hợp bundle V4 thực.
- [x] Adapter kiểm SHA-256 của bundle, giữ `course_id` và `course_family_id` trong
  prediction artifacts để tính endpoint cấp khóa/family.

## 4. Việc phải làm ngay khi nhận CQ V4

### 4.1. Gate bàn giao dữ liệu trước khi chạy máy

- [x] Đủ runtime files bắt buộc để chạy dev V4.
- [x] `dataset_version` thống nhất là CQ V4.
- [x] `bundle_manifest.test_excluded=true`; không có test parquet/CSV/NPY trong bundle.
- [x] `splits.json`: group unit thực tế là `course_family_id`, seed 42, tỷ lệ 70:10:20.
- [x] 26/26 hash của split, feature list, preprocessing, manifest và Parquet khớp.
- [x] Không giao family giữa train/dev; test assignment chỉ kiểm metadata/hash ở M0,
  không mount feature/label test.
- [x] Có sensitivity Jaccard 0,8 bên cạnh split chính 0,9.
- [x] Có concentration, temporal overlap 75,7998% và `requires_nolfo=true`.
- [x] Pool B có train và dev P1–P4, hai feature view, metadata thẳng hàng.
- [x] FullTrain-A lambda=1 đúng 131.906 enrollment của train Pool B, không có dev/test row.
- [x] Data card ghi class distribution, family/course/enrollment, lớp E, `nc>=30`, ICC,
  sàn EC và old/new user/instructor.
- [ ] Xin duyệt bằng văn bản việc không đối chiếu TEMPO-DQ theo phạm vi người dùng chốt.

### 4.2. Prepare và kiểm tra code

- [ ] Chạy adapter V4:

  ```powershell
  skq prepare-external --config configs/cq_v4_m0_fulltrain_b_dev_natural_xgb_v1.json `
    --dataset course_quality_v4 --input-dir <THU_MUC_CQ_V4> --overwrite
  ```

- [ ] Lưu `preprocessing_manifest.json`, `feature_contract.json`,
  `split_manifest.json` và SHA-256 vào archive M0-V4.
- [ ] Chạy toàn bộ pytest, không chỉ sáu test mới:

  ```powershell
  python -m pytest -q
  ```

- [ ] Ghi Python/package/GPU/CPU/RAM/commit vào environment manifest.

### 4.3. Chạy FullTrain-A và FullTrain-B trên dev

- [ ] FullTrain-B XGB natural:

  ```powershell
  skq run --config configs/cq_v4_m0_fulltrain_b_dev_natural_xgb_v1.json --resume
  ```

- [ ] FullTrain-A XGB natural:

  ```powershell
  skq run --config configs/cq_v4_m0_fulltrain_a_dev_natural_xgb_v1.json --resume
  ```

- [ ] Báo P1–P4 và pooled summary: Macro-F1, MCC, balanced accuracy, log loss, ECE,
  ROC-AUC/PR-AUC, confusion matrix và precision/recall/F1/PR-AUC từng lớp.
- [ ] Báo endpoint course: EC, signed deviation, số course có `nc>=30`.
- [ ] Chạy A8 prior correction không retrain; ghi rõ nguồn prior V4.
- [ ] Chạy lưới LR 8 cấu hình; lưu convergence status và iteration count.

### 4.4. Chạy headroom và khóa rho star

- [ ] Chạy lần lượt bốn config:

  ```text
  configs/cq_v4_m0_headroom_c02_rho005_natural_v1.json
  configs/cq_v4_m0_headroom_c02_rho01_natural_v1.json
  configs/cq_v4_m0_headroom_c02_rho02_natural_v1.json
  configs/cq_v4_m0_headroom_c02_rho05_natural_v1.json
  ```

- [ ] Mỗi mức đủ 5 seed × 4 dev phase; không dùng phase như replicate độc lập.
- [ ] Chạy `scripts/compute_cq_v4_headroom.py` với đủ bốn `--c02-config`.
- [ ] Báo mean, SD, SE, Delta FullTrain-B − C02, cờ gap 0,01 và rho*.
- [ ] Chạy 2.000 family bootstrap cho FullTrain-B − C02; báo 95% CI half-width.
- [ ] Không đổi rho* sau khi xem candidate SKQ.

### 4.5. Chạy QĐ16 tại rho star

Mỗi dòng phải có wall time, CPU time nếu có, peak RSS, passes over train, trạng
thái success/TIMEOUT/OOM/blocked, quy mô đo, quy tắc ngoại suy và trần 3 giờ.

- [ ] C01 Uniform Random.
- [ ] C02 Stratified Random.
- [ ] C03 phase × class random, proportional để mô tả.
- [ ] CoreTab-XGB native.
- [ ] BDIS native.
- [ ] GCoreSet.
- [ ] Moderate-DS adapted.
- [ ] CCS OOF-XGB adapted.
- [ ] Data-OOB official adapter.
- [ ] Kernel Thinning adapted classwise Compress++.
- [ ] CoreTab-XGB OVA adapted.
- [ ] SKQ-PC.
- [ ] SKQ-PC + LRQ-SQ.
- [ ] SKQ-PC-√.

**Gate Kernel Thinning:** chạy fidelity trước. Nếu shard wrapper vẫn dự báo hoặc
đo vượt 10.800 giây, ghi `TIMEOUT`, giữ log/checkpoint và không để nó chặn M1.

### 4.6. Chạy kiểm tra 1–12 và probes trên V4

- [ ] Contract ID/row uniqueness và family leakage.
- [ ] Train-only preprocessing, feature view và target leakage.
- [ ] Missingness/mask.
- [ ] Cutoff/phase monotonicity và snapshot contract.
- [ ] Label formula/version và class counts.
- [ ] Shuffled-label probe.
- [ ] Majority baseline probe.
- [ ] FullTrain-A cohort consistency.
- [ ] Exact budget/class coverage/mass conservation cho selector.
- [ ] QP convergence và constraint validity.
- [ ] Artifact/privacy/storage gates.
- [ ] Test lock và freeze gate.

## 5. Việc sau khi rho star được khóa và trước M1

- [ ] Tạo config panel dev V4 tại rho*; không sửa đè config headroom.
- [ ] Chạy 10 selector cố định + CoreTab OVA + 3 candidate, ba seed, XGB natural.
- [ ] Chạy C03 cùng allocation với winner; giữ C03 proportional trong bảng mô tả.
- [ ] Chạy A2 cùng allocation với winner, A4 no-QP, A8 prior correction.
- [ ] Chạy A3 SKQ-PC-R cho luận văn/appendix, không dùng để chọn candidate.
- [ ] Chọn winner theo dev; nếu chênh dưới 0,002 chọn candidate rẻ hơn.
- [ ] Báo paired effect theo block và family bootstrap; không coi learner/phase là replicate.
- [ ] Cập nhật novelty ledger và references.
- [ ] Tạo protocol manifest M0-V4 đã duyệt.
- [ ] Ngày 08/11: khóa M1 freeze manifest; chỉ sau đó mới chuẩn bị mở test một lần.

## 6. Những việc tuyệt đối chưa làm ở M0 V4

- [x] Không đọc hoặc evaluate test V4.
- [x] Không tune bằng test.
- [x] Không dùng số V1/V3 để chọn rho, candidate hay hyperparameter trên V4.
- [x] Không gọi P4 là FullTrain-A.
- [x] Không thay method lỗi/TIMEOUT bằng proxy không khai báo.
- [x] Không commit raw row, predictions, selected indices, sample weights hoặc token.
- [x] Không gửi GitHub token/Kaggle secret cho giảng viên.

## 7. Kết quả lịch sử được phép nêu nhưng không dùng để chọn trên V4

| Bằng chứng lịch sử | Kết quả chính | Ý nghĩa được phép dùng |
| :-- | :-- | :-- |
| FullTrain-B dev V1 | XGBoost natural tốt nhất ở UL và EC; balanced/A8 giảm EC nhưng giảm UL; LR 8 fit chưa hội tụ | Mô tả động cơ chọn natural và cần tune LR; không suy ra kết quả V4 |
| Headroom dev V1 | 52/52 lượt hoàn tất; không mức nào đạt gap theo quy tắc; fallback rho*=0,5%; SD seed 0,013–0,021 | Chứng minh pipeline chạy và lực thống kê V1 yếu; phải chạy lại V4 5 seed |
| Pilot SKQ 2% V1 | SKQ-PC chuẩn thấp hơn C02/C03; LRQ-SQ gần C03 về Macro-F1 nhưng recall E thấp và chậm khoảng 70 lần | Động cơ thay candidate R bằng sqrt allocation; không chọn winner V4 |
| QĐ16 V1 | 9/13 phương pháp đã đo; tất cả cận trên dưới 3 giờ ngoại trừ Kernel Thinning cũ chưa xong | Dùng lập lịch ban đầu; phải đo lại KT Compress++ và panel đủ tại rho* V4 |
| EDA V1/V3 | V1 dev có course lớn nhất 53%; V3 có 284 cặp course Jaccard ccid ≥0,9 | Động cơ dùng family split và family bootstrap |

## 8. Bộ sản phẩm phải đính kèm khi gửi giảng viên ngày 29 tháng 10

### 8.1. Bắt buộc

- [ ] Báo cáo M0-V4 PDF/MD, có bảng đối chiếu checklist này.
- [ ] `DATA_CARD_V4.md` và `COURSE_FAMILY_SENSITIVITY.md`.
- [ ] `splits.json`, `family_splits.parquet`, `course_splits.parquet` và SHA-256.
- [ ] `validation.json`, kết quả kiểm tra 1–12 và data/build manifest.
- [ ] Archive FullTrain-A/B dev V4 gồm ledger, metrics tổng, per-label, course endpoint,
  confusion matrices và environment/commit manifest; không có raw prediction dòng nếu không gửi riêng an toàn.
- [ ] Archive headroom V4 gồm đủ 5 seed, bốn rho, decision JSON và CI family-bootstrap.
- [ ] Archive QĐ16 gồm ledger 14 method, checkpoint, TIMEOUT/OOM và dự báo lịch chạy.
- [ ] File kết quả pytest toàn repo và riêng `test_cq_patch_1022.py` 6/6.
- [ ] Link PR/diff trên GitHub, commit hash và tag `review-2026-10-22` sau khi merge.
- [ ] `references.bib` và novelty ledger cập nhật.

### 8.2. Không đính kèm

- [x] Không gửi GitHub personal access token.
- [x] Không gửi Kaggle secret hoặc notebook chứa secret value.
- [x] Không commit raw/private row data lên repo.
- [x] Không gửi test feature/label trước M1 freeze.

### 8.3. Link cần ghi rõ trong email

- [ ] URL repo công khai.
- [ ] URL nhánh/PR chứa lô sửa Review 22/10.
- [ ] Commit hash chính xác dùng để chạy notebook.
- [ ] Link notebook Kaggle và version đã chạy; quyền xem nếu notebook private.
- [ ] Link dataset V4 dev-only; quyền truy cập nếu dataset private.
- [ ] Hash từng archive kết quả tải về.

## 9. Gate để báo cáo trung thực tại điểm kiểm tra

### READY FOR M0 V4 REVIEW

Chỉ đánh dấu khi đồng thời:

- [ ] CQ V4 qua contract và không có test trong runtime bundle.
- [ ] FullTrain-A/B dev V4 thành công và có metrics tổng/per-class/course.
- [ ] Headroom đủ 5 seed × 4 rho; rho* và CI được khóa.
- [ ] QĐ16 đủ 14 method hoặc có TIMEOUT/OOM hợp lệ theo rule.
- [ ] Kiểm tra 1–12 và pytest đạt.
- [ ] PR, commit, tag, references và novelty ledger sẵn sàng.

### Chưa được gọi là GO M1 hoặc GO bài báo

M0-V4 ngày 29/10 là điểm kiểm tra dữ liệu, rho*, tham số và lịch chạy. Việc hoàn
thành checklist này cho phép tiếp tục panel dev đến M1; nó không tự động chứng
minh phương pháp thắng baseline, không mở test và không bảo đảm chấp nhận bài.

## 10. Nhật ký cập nhật

| Ngày giờ | Người cập nhật | Thay đổi | Bằng chứng |
| :-- | :-- | :-- | :-- |
| 22/10/2026 | Nhóm thực nghiệm | Sửa allocator/candidate, C03, Compress++, family protocol, bootstrap, adapter FullTrain-A/V4, config headroom 5 seed | 62/62 targeted tests; 194/194 full regression; 6 config V4 validate |
| 22/10/2026 | Nhóm thực nghiệm | Nhận và validate CQ V4 dev-only; sửa adapter theo schema bàn giao | 26/26 SHA khớp; 188/188 validation; 14/14 independent; ingest thành công; 195/195 test |
|  |  | Chạy FullTrain-A/B |  |
|  |  | Chạy headroom và khóa rho* |  |
|  |  | Chạy QĐ16 |  |
|  |  | Hoàn thiện PR/tag/gói gửi giảng viên |  |
