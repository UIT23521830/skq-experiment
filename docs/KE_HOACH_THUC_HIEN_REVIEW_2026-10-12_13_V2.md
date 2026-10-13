# Kế hoạch thực hiện Review 12–13/10/2026 — V2

## 0. Kiểm soát tài liệu

| Trường | Giá trị |
|---|---|
| Trạng thái | `DRAFT_FOR_CONFIRMATION` — chỉ là kế hoạch, chưa cho phép sửa thuật toán hoặc mở test |
| Phiên bản kế hoạch | `2.0.0-draft` |
| Ngày lập | 14/10/2026 |
| Nhánh dùng để soạn | `cq-v1-protocol-fixes` |
| Commit nền đã kiểm tra | `acd2d9f62d7f199abef16eb943b28f9c0c9e145e` |
| Review 12/10 SHA-256 | `3C48CAAA4024FF9A7D19F948428142586BE0097849319B45B056BE39880538AB` |
| Review 13/10 SHA-256 | `35F6CE05910ACEB5777610B482FC9D12BD14FF35E0E0FD8590D26C79970E8EA2` |
| Tài liệu tiền nhiệm | `docs/KE_HOACH_THUC_HIEN_REVIEW_2026-10-12_13.md` |
| Phạm vi của V2 | Kế hoạch code, dữ liệu, kiểm định, bằng chứng, phiên bản, rollback và câu hỏi cần xác nhận |
| Ngoài phạm vi ở bước này | Chưa sửa code production, chưa đổi config confirmatory, chưa chọn winner, chưa mở CQ v1 test |

Mỗi lần sửa kế hoạch sau khi được duyệt phải tăng `plan_version`, thêm changelog và
ghi commit nền mới. Không ghi đè evidence hoặc freeze manifest đã phát hành.

### 0.1. Changelog so với V1

1. Thêm ma trận ánh xạ requirement → file/symbol thực tế → file đích → test → evidence.
2. Tách temporal và StratifiedGroupKFold thành decision gate loại trừ lẫn nhau.
3. Khôi phục timeline, GO/NO-GO, Plan B và rollback từ hai review.
4. Định nghĩa taxonomy `native/adapted/proposed/binary-only` có thể kiểm tra bằng code.
5. Định nghĩa từng quality gate, tiêu chí đạt, evidence và hành động khi không đạt.
6. Định nghĩa state machine dev → M0 → M1/freeze → test.
7. Định nghĩa H0/H1, chiều kiểm định, alpha, Holm và schema báo cáo K1–K5/K1c–K5c.
8. Đưa mã tham chiếu ở Phụ lục E review 12 và Phụ lục B review 13 vào ma trận tích hợp.
9. Thêm versioning cho traceability, Claim Ledger và liên kết `run_id`.
10. Bổ sung encoding, privacy audit, owner, dependency, rollback và acceptance criteria.
11. Bổ sung mục xin xác nhận về một candidate CoreTab multiclass, không tự ý tăng phạm vi.

## 1. Nguyên tắc điều hành

### 1.1. Thứ tự ưu tiên nguồn

1. Quyết định ngày 13/10 (QĐ12–QĐ17) thay thế phần tương ứng ngày 12/10.
2. Quyết định ngày 12/10 (QĐ1–QĐ11) vẫn có hiệu lực nếu không bị thay thế.
3. Mã ở phụ lục là mã tham chiếu đặc tả; không chép nguyên nếu không khớp kiến trúc hiện tại.
4. Pilot Adult/CQ_med đã mở test chỉ là exploratory; không được dùng để chọn cho CQ v1.
5. CQ v1 là dữ liệu chính; Adult và Covertype chỉ dùng kiểm tra tính tổng quát sau freeze.

### 1.2. Các điều cấm

- Không dùng test để chọn split, `rho*`, policy trọng số, learner, baseline mạnh nhất,
  candidate SKQ-PC hoặc siêu tham số.
- Không freeze hồi tố kết quả CQ_med đã xem.
- Không đổi tên P07/P08/P02 thành SKQ-PC hoặc CoreTab native.
- Không gọi CoreTab OVA là native multiclass.
- Không dùng từ “SOTA”; chỉ dùng “non-inferior” khi kiểm định đăng ký trước đạt.
- Không loại phương pháp chỉ bằng operation count chưa hiệu chuẩn.
- Không pad, lặp hoặc cắt native output mà không khai báo contract.
- Không đẩy dữ liệu, predictions, selected indices, sample weights hoặc định danh dòng lên nơi công khai.
- Không ghi `DONE` nếu thiếu đồng thời code, test và evidence.
- Không force-push/ghi đè tag, manifest hoặc artifact đã gửi đánh giá.

### 1.3. Định nghĩa trạng thái

| Trạng thái | Ý nghĩa |
|---|---|
| `NOT_STARTED` | Chưa có code/test/evidence |
| `PLANNED` | Có trong kế hoạch, chưa triển khai |
| `IN_PROGRESS` | Đã có thay đổi nhưng chưa qua gate |
| `IMPLEMENTED_UNVERIFIED` | Có code, thiếu test hoặc evidence |
| `VERIFIED_DEV` | Đạt test và evidence trên dev |
| `FROZEN_M0` | Tham số giao thức được khóa tại M0 |
| `FROZEN_M1` | Phương pháp/config được khóa trước test |
| `CONFIRMATORY_COMPLETE` | Test được mở đúng manifest và kết quả hoàn tất |
| `EXPLORATORY_ONLY` | Chỉ dùng mô tả/nội bộ, không tạo claim confirmatory |
| `BLOCKED_EXTERNAL` | Thiếu dữ liệu, source, dependency hoặc quyết định ngoài code |
| `FAILED_GATE` | Không đạt một gate; phải dừng phạm vi bị ảnh hưởng |
| `RETIRED_FROM_CONFIRMATORY` | Giữ code để tái lập lịch sử, không chạy CQ v1 confirmatory |

## 2. Phạm vi học thuật đã chốt

### 2.1. Câu hỏi chính

Đánh giá coreset cho dự đoán sớm chất lượng vận hành của khóa học mới, với:

- đơn vị gốc là lượt ghi danh `(learner, course offering)`;
- nhãn cấp người học `y_kc = tau(q_kc)`;
- bốn snapshot P1–P4;
- đánh giá chính theo lượt ghi danh trên khóa test mới;
- endpoint phụ là sai số tổng hợp lên cấp khóa học;
- cùng pool, preprocessing, budget, learner protocol và chính sách trọng số.

### 2.2. Hai kịch bản không được trộn

| Kịch bản | Mục đích | Split | Vai trò |
|---|---|---|---|
| Thiết kế chính | Khả năng chuyển giao sang khóa học mới | Temporal theo khóa hoặc SGKF theo quyết định M0 | Confirmatory CQ v1 |
| TEMPO-DQ vận hành | Đối chiếu khóa/người học cũ–mới | Stratified 8:1:1 theo instance | RQ5, mô tả, không nằm bảng chính |

### 2.3. Phương pháp trong bài chính

- FullTrain-A, FullTrain-B.
- C01 Uniform random, C02 Stratified random theo lớp.
- C03 Stratified random phase × class có bảo toàn khối lượng.
- k-Center/Gonzalez, Moderate-DS, CCS, Data-OOB, Kernel thinning/Compress++.
- CoreTab-XGB OVA `adapted` tại `rho*`.
- BDIS native, báo realized size và Pareto; so random và SKQ-PC cùng realized size.
- Một phương pháp đề xuất chốt: SKQ-PC.
- A2 và A4 trong phạm vi bài; các ablation khác theo nhánh/timeline.
- AutoCoreset chỉ bắt buộc nếu SKQ-PC chốt dùng LRQ.
- Synthetic ngoài phần chính.

## 3. Taxonomy phương pháp và quy tắc gán nhãn

### 3.1. Trường metadata bắt buộc trong registry

`MethodSpec` sẽ được mở rộng bằng các trường có enum/validation:

```text
scientific_role:
  reference | control | native_baseline | adapted_baseline |
  benchmark_source | proposed_candidate | proposed_frozen |
  ablation | appendix_only | historical | retired

fidelity_tier:
  official_native_path | official_source_adapter |
  official_source_with_declared_patches | benchmark_source_adapter |
  local_reimplementation | proposed

task_contract:
  binary_only | multiclass | regression | task_agnostic

budget_contract:
  exact | native_realized | at_most | synthetic_exact | not_applicable

evidence_role:
  exploratory | dev_selection | confirmatory | appendix
```

Các trường đi kèm:

```text
upstream_url, upstream_commit, declared_patches, adaptation_reason,
max_dev_configs, allowed_learners, output_kind, supports_sample_weight,
supports_sharding, public_evidence, private_evidence
```

### 3.2. Tiêu chí `native`

Một run chỉ được ghi `native` khi đồng thời:

1. Gọi đường thuật toán chính thức ở commit đã khóa.
2. Nhiệm vụ đầu vào nằm trong task contract mà source/paper hỗ trợ.
3. Không đổi objective, label transformation, quota, union rule, budget semantics hoặc selection rule.
4. Thay đổi I/O chỉ là compatibility adapter và được ghi lại.
5. Test toy/example của source đạt ở mức hợp lý.

Nếu vi phạm mục 2 hoặc 3 thì phải là `adapted`, dù source chính thức vẫn được gọi.

### 3.3. Tiêu chí `binary_only`

- Metadata upstream xác nhận phạm vi nhị phân.
- Fixture 3 lớp phải trả `na_contract`, không tự fallback.
- Nếu chỉ xuất leaf structure cho proposed thì artifact ghi
  `structure_only=true`, `reference_equivalent_subset=false`.
- Native row không có Macro-F1 multiclass; bảng ghi “binary only”.

### 3.4. Tiêu chí `adapted`

Phải gắn `adapted` nếu có ít nhất một thay đổi có ý nghĩa:

- OVA/OVR, ECOC hoặc chuyển đổi label;
- union/chọn lại output của nhiều lần chạy;
- quota theo lớp/phase;
- đổi objective binary sang multiclass;
- patch gradient, RNG, snapshot hoặc training loop;
- thay đổi budget/output semantics;
- dùng một stage của source nhưng bỏ pipeline chính thức còn lại.

Evidence bắt buộc: lý do adaptation, patch list, upstream commit, test contract,
khác biệt với paper, và claim bị cấm.

## 4. Phân loại code hiện tại

| Nhóm hiện tại | Vai trò sau review | Hành động |
|---|---|---|
| P01–P05, P09–P11 | `RETIRED_FROM_CONFIRMATORY` | Giữ để tái lập pilot; confirmatory config từ chối |
| P06 | `appendix_only` | Chỉ đo đóng góp QP trên Gonzalez |
| P07/P08 | `historical precursor` | Có thể đối chiếu/ablation; không gọi SKQ-PC |
| P00 engine | `internal engine` | Không là một dòng utility |
| Synthetic | `out_of_scope_main_study` | Không chạy GĐ0/GĐ1 |
| CRAIG feature-space | `adapted/appendix` | Không ghi native CRAIG |
| CoreTab native | `binary_only_native` | Multiclass trả `na_contract` |
| CoreTab OVA | `adapted_confirmatory_baseline` | Cài theo QĐ14 |
| BDIS | `native_pareto_baseline` | Giữ realized size |
| SKQ-PC candidates | `proposed_candidate` | Tối đa ba candidate active |
| SKQ-PC winner | `proposed_frozen` | Chỉ sau chọn dev và M1 |

Registry hiện tại vẫn ghi nhiều P là `proposed/implemented`; đây là gap phải sửa trước
khi tạo config CQ v1, nhưng không xóa implementation lịch sử.

## 5. Ma trận ánh xạ requirement → repo

| ID | Yêu cầu | Hiện trạng/symbol thực tế | Đích dự kiến | Test/evidence | Fail action |
|---|---|---|---|---|---|
| QĐ1/R1 | CQ là dữ liệu chính | Config chính vẫn là pilot Adult/CQ_med | `configs/cq_v1/*`, docs scope | Config audit | Không chạy confirmatory nếu CQ v1 chưa hợp lệ |
| QĐ2/R2/O6 | Một SKQ-PC, tối đa 3 candidate; thu hẹp phạm vi và số kiểm định | `methods/registry.py` còn P01–P11 active | registry roles + `proposed/skq_pc.py` | role/config tests | Từ chối retired method trong CQ v1 |
| QĐ3/O1 | Split theo khóa | CQ_med adapter đọc pre-split instance | `data/cq_protocol.py`, `course_quality_v1.py` | split/data checks | Dừng selector |
| QĐ4 | Timeline/GO | V1 không có lịch chi tiết | Mục 25 V2 | milestone ledger | Chuyển NO-GO nếu trễ đường găng |
| QĐ5 | Quy tắc định vị tại M1 | Chưa machine-readable | freeze + report decision | dev decision artifact | Không claim phương pháp nếu điều kiện không đạt |
| QĐ6/O2/O3 | Seed, bootstrap, Pareto | Metrics hiện chưa đủ hai cấp | `training/statistics.py`, reports | stats tests | Kết quả chỉ descriptive |
| QĐ7/QĐ17/O10/O18 | Quyền riêng tư/phiên bản | `.gitignore`, archive cơ bản | privacy audit + release manifest | `privacy_audit.json` | Chặn public release |
| QĐ8/O8/Y4/Y13 | Tài nguyên đo thật | `resources.py` gate operations | `resource_calibration.py` | scaling/RSS evidence | shard hoặc TIMEOUT |
| QĐ9/O13 | Dòng là enrollment | `course_quality.py` đọc row chương | `enrollment_table` production | unique enrollment test | Dừng và báo giảng viên |
| QĐ10 | Qc/Yc | Chưa có | `course_metrics.py` | recompute 1e-9 | Không báo EC |
| QĐ11 | UL/EC | Metrics chủ yếu row-level | metrics + course aggregation | endpoint tests | Không tạo bảng chính |
| QĐ12 | Headroom `rho*` | Budget pilot cố định | `headroom_budget` + M0 config | 4 mức × 3 seed | Không chạy K1–K5 |
| QĐ13/Y8 | Test mới và freeze | freeze schema v3 thiếu trường | freeze schema v4 + runner gate | freeze state tests | Không đọc test |
| QĐ14/Y11 | CoreTab OVA adapted | Chưa có package adapted | `methods/adapted/coretab_ova.py` | quota/no-padding tests | Row CoreTab ghi blocked/failed |
| QĐ15/O11/O14 | Mean-one weights | `effective_sample_weights` chưa normalize | `weights.py`, evaluator, runner | 2 test review + edge tests | Chặn mọi run so sánh |
| QĐ16/O15 | Bỏ `5e10` gate | `resources.enforce_preflight` còn chặn | calibration + diagnostic ops | measured evidence | Không dùng predicted_ops để loại |
| O16/Y5 | Tune/early stopping dev | evaluator chỉ MLP nhận eval set | evaluator/learners/runner/config | spy/no-test tests | Chặn run confirmatory |
| O17 | ID không là tọa độ selector | Dùng chung matrix | `selector_view` + schema | drop-ID/alignment tests | Chặn selector hình học/kernel |
| O4 | Synthetic bất thường | Có implementation nhưng ngoài scope | Giữ historical | config test | Không chạy GĐ0/GĐ1 |
| O5 | 6 baseline thiếu | Chưa có modules tương ứng | modules baseline/adapters | upstream toy tests | Báo missing baseline; không tự thay proxy |
| O7 | Nguồn/cách tính CQ | Chưa có CQ v1 data card | private data card + public schema/hash | provenance audit | Dừng M0 |
| O9 | Literature/novelty | Ma trận chưa đủ | novelty table/BibTeX | manual review evidence | Không claim novelty |
| O12 | Khóa lớn/nhỏ | Chưa có sensitivity | course-weighted endpoint, `n_min` | stats evidence | Báo limitation |
| Y1 | Số liệu lệch phiên bản | Bảng thủ công | reports từ `runs_long` | generated table hash | Không cập nhật bằng tay |
| Y2 | BibTeX | Có lỗi #10 | sửa tài liệu | BibTeX validation | Không chốt bibliography |
| Y3 | Tên/source | Registry chưa thống nhất | taxonomy/display name | docs snapshot | Không xuất bảng tên cũ |
| Y6 | 90 metrics | Quá rộng | core metrics + appendix | schema test | Bảng chính chỉ metrics lõi |
| Y7 | Kế hoạch tuần | V1 không timeline | Mục 25 + weekly status | status ledger | Cập nhật hàng tuần |
| Y9/Y10 | Thuật ngữ/cấp đánh giá | Chưa bắt buộc | report schema | column validation | Không xuất bảng thiếu metadata |
| Y12 | Seed 0 | Chưa giải thích | seed provenance | config/run check | Ghi deterministic hoặc sửa |
| Y14 | CatBoost gián đoạn | Pilot thiếu | extension only | role test | Không chạy lại GĐ0 |
| Y15 | Tag/PR/Save Version | Một phần | release checklist | tag/PR/version links | Không gửi review |
| Y16 | Owner | Chưa có | owner matrix | review checklist | Không bắt đầu task không owner |

## 6. Giao thức CQ v1

### 6.1. Schema tối thiểu

| Cột | Cấp | Bắt buộc | Vai trò |
|---|---|---:|---|
| `course_id` | lần mở khóa | Có | tổng hợp Qc, mốc cắt; không làm feature |
| `course_root_id` | khóa gốc | Có | split/bootstrap; không làm feature |
| `learner_id` hoặc mã hóa tương ứng | enrollment | Có | đối tượng cũ/mới; learner feature theo TEMPO-DQ |
| `teacher_id`, `school_id` | enrollment | Theo nguồn | learner feature, không là selector coordinate |
| `enroll_time`, `course_start`, `course_end` | enrollment/course | Có cho temporal | cutoff và split |
| `q` | enrollment | Có | Qc, mu_y, ICC, EC; không làm feature |
| `y` | enrollment | Có | train/UL |
| thành phần COELO/AFELO/ACELO hoặc bảng chương | nguồn nhãn | Có để truy nguyên | tái lập q; không làm feature |
| `phase`, `cutoff_time` | snapshot | Có | P1–P4, Pool B |
| `split` | course/root | Có | train/dev/test |
| features tại cutoff | snapshot | Có | learner/selector view sau lọc |

### 6.2. Đơn vị và nhãn

1. Một dòng enrollment duy nhất cho `(course_id, learner_id)`.
2. `q_kc` là trung bình LOQV qua các chương theo quy tắc data card.
3. LOQV phải có cờ scale rõ ràng; production không tự đoán chỉ từ `max <= 1`.
4. `y = E` nếu `q < 0.2`, `G` nếu `0.2 <= q < 0.4`, `A` nếu còn lại.
5. Quy ước đúng tại biên 0.2/0.4 phải có unit test.
6. Nhãn cố định qua P1–P4; features được tính lại theo cutoff.
7. Nếu mọi learner trong một khóa có cùng nhãn, dừng và báo giảng viên.

### 6.3. Pool

- FullTrain-A: cách train nguyên của TEMPO-DQ trên khóa train.
- Pool B/FullTrain-B: bốn snapshot P1–P4 cho mỗi enrollment thuộc khóa train.
- Mọi selector trong bảng chính nhận cùng Pool B.
- Pha được giữ như feature chỉ khi protocol quy định; phase/class luôn tồn tại dưới
  dạng metadata để stratify và audit.

## 7. Decision gate cho split

Temporal và SGKF là hai nhánh loại trừ lẫn nhau, không phải hai bước chạy nối tiếp.

### 7.1. Input cho quyết định M0

- tỷ lệ timestamp thiếu/không parse được;
- tính nhất quán `course_start <= course_end`;
- số course root và enrollment theo lớp;
- số khóa/lớp dự kiến trong train/dev/test;
- nửa độ rộng CI bootstrap dev;
- tỷ lệ train course chưa kết thúc khi test đầu tiên mở;
- drift nhãn theo thời gian;
- số lần mở trên mỗi `course_root_id`.

### 7.2. Quy tắc

```text
Nếu timestamp đáng tin cậy
và temporal 70/10/20 giữ đủ lớp
và test có ít nhất 10 khóa trong mỗi lớp
và nửa độ rộng CI dev không vượt 0,005:
    chọn TEMPORAL_70_10_20
ngược lại:
    chọn SGKF_5_FOLD_X_2
```

Ngưỡng “10 khóa/lớp” và “0,005 CI half-width” lấy từ review, nhưng phải được
giảng viên xác nhận tại M0 theo data card. Không được thay ngưỡng sau khi xem test.

### 7.3. NOLFO sensitivity

Nếu temporal được chọn nhưng tỷ lệ khóa train chưa kết thúc khi khóa test đầu tiên
mở lớn hơn 5%, chạy thêm phương án loại các khóa đó khỏi train cho FullTrain-B và
SKQ-PC. Đây là sensitivity, không phải lý do tự động đổi sang SGKF.

### 7.4. Evidence

`split_decision.json` gồm:

```text
schema_version, decision, reasons, thresholds, diagnostics,
course_counts_by_class, ci_half_width_dev, overlap_rate,
splits_sha256, source_commit, created_at, approved_at_m0
```

## 8. Mười hai kiểm tra dữ liệu bắt buộc

| ID | Kiểm tra | Pass criterion | Evidence | Fail action |
|---|---|---|---|---|
| D01 | Kích thước/phân bố | Có course, enrollment, row, nhãn theo split/phase; group disjoint | `data_audit.json` | Dừng |
| D02 | ID-only probe | Course ID ở thiết kế chính xấp xỉ majority; báo teacher/school/learner | `id_probe.parquet` | Kiểm tra leakage/split |
| D03 | Missingness probe | Tái lập probe TEMPO-DQ; không đưa missing mask vào features | `missingness_probe.json` | Sửa pipeline |
| D04 | Permuted-label | XGB FullTrain-B dev về mức ngẫu nhiên | `label_shuffle.json` | Dừng, audit leakage |
| D05 | Floor | Majority theo phase; provisional metric nếu có | `floor_metrics.parquet` | Chỉ báo limitation nếu thiếu provisional |
| D06 | Cutoff | 20 cặp thủ công: max event time <= cutoff ở mọi phase | checklist + sampled IDs private | Dừng snapshot generation |
| D07 | Weight contract | Mass error ~0 cho C03/SKQ-PC; all-one/zero/scaling đạt | pytest + weights summary | Chặn train |
| D08 | Baseline reproduction | Toy/example upstream đạt mức hợp lý | baseline evidence | Không đưa baseline vào bảng; báo blocker |
| D09 | Enrollment/label | Mỗi cặp duy nhất; `y=tau(q)`; có within-course label variation | pytest + data audit | Dừng và báo giảng viên |
| D10 | Label leakage | q/y/components/derived labels không trong X | feature schema | Dừng |
| D11 | Course recomputation | Qc khớp data card sai số < 1e-9; báo Yc mỗi split | course audit | Dừng EC |
| D12 | Protocol constants | `mu_E < mu_G < mu_A`, mỗi mu nằm đúng class range | protocol constants JSON | Dừng aggregation |

D01–D07 và D09–D12 phải đạt trước M0. D08 phải đạt trước M1.

## 9. Trọng số huấn luyện QĐ15

### 9.1. Contract

Cho mọi run, kể cả FullTrain:

```text
raw_i = method_weight_i * class_weight[y_i]
effective_i = raw_i * n / sum(raw)
mean(effective) = 1
```

Class weight policy là `natural` hoặc `balanced`, chọn tại M0 bằng FullTrain-B
trên dev, báo cả UL và EC. Không tính class weight lại từ coreset.

### 9.2. Vị trí sửa

- `src/skq_exp/training/weights.py`
- `src/skq_exp/training/evaluator.py`
- `src/skq_exp/experiments/runner.py`
- `src/skq_exp/reports/aggregate.py`
- `tests/test_weights.py`

### 9.3. Điều chỉnh mã mẫu review 13

- Công thức mean-one dùng được.
- Không chỉ sửa `fit_selection_learner`; phải dùng chung cho selection, generated,
  FullTrain-A/B và mọi learner.
- Policy class weight phải là config field được hash và freeze.
- Không ghi toàn bộ vector weight vào public artifact.

### 9.4. Evidence mỗi run

```text
weight_policy, raw_sum, normalization_factor, effective_sum,
effective_mean, effective_min, effective_max, weighted_class_prior
```

### 9.5. Test

- `test_xgb_depends_on_weight_scale_until_normalized` từ review.
- `test_normalization_keeps_prior_and_mean_one` từ review.
- all-one giữ mean 1.
- zero weight hợp lệ nếu tổng dương; all-zero bị từ chối.
- negative/NaN/Inf/shape mismatch bị từ chối.
- scaling method weights bởi hằng số không đổi output effective.
- mọi đường evaluator dùng cùng helper.

## 10. Selector view và learner view

### 10.1. Contract

- Selector hình học/kernel không dùng mọi cột mã định danh làm tọa độ.
- Learner vẫn nhận các mã được TEMPO-DQ cho phép, sau preprocessing fit trên train.
- Selected indices luôn tham chiếu vào row order của matrix learner gốc.
- Feature schema và dropped columns được lưu theo run.

### 10.2. Điều chỉnh mã mẫu

`selector_view` ở review chỉ là reference. Production phải:

- dựa trên schema/semantic role, không chỉ danh sách tên cứng;
- phân biệt ID, target, target-derived, metadata và feature;
- kiểm tra sau transform không còn ID coordinate;
- giữ row ID mapping riêng, không đưa row ID vào matrix.

### 10.3. Test

- test từ review: drop đúng ID columns.
- hoán vị giá trị ID không làm thay đổi selection.
- indices trả về chọn đúng row trong learner view.
- q/y/COELO/AFELO/ACELO và target-derived luôn bị loại.

## 11. Learner tuning và early stopping

### 11.1. Quy trình

1. Khai báo grid trước khi chạy.
2. Tune tối đa 8 cấu hình/learner trên FullTrain-B và dev.
3. Khóa cấu hình learner tại M0/M1 theo phạm vi review.
4. Dùng cùng cấu hình cho mọi method.
5. Mỗi run early-stop trên dev theo cùng quy tắc.
6. Test không đi vào `fit`, `eval_set`, threshold hoặc best iteration.

### 11.2. Mã mẫu review 13

Patch minh họa không được chép theo số dòng cũ. Tích hợp theo symbol:

- evaluator truyền dev cho MLP và XGB;
- wrapper XGB expose early stopping đúng API phiên bản đã khóa;
- log `best_iteration`, `eval_metric`, patience và library version;
- model khác không có early stopping phải ghi `not_supported`, không giả lập.

### 11.3. Test

- Spy xác nhận dev được truyền, test không được truy cập.
- XGB dừng trước 1.000 cây trên fixture phù hợp.
- Cùng frozen params cho mọi method.
- `best_iteration` có trong ledger.
- Thiếu dev ở confirmatory config là lỗi contract.

## 12. Resource calibration QĐ16

### 12.1. Thay đổi contract

- `estimated_operations` chỉ là diagnostic.
- Không trả `predicted_timeout` chỉ vì vượt `5e10`.
- Wall-clock và RSS thực tế vẫn là safety guard.
- Đo selector trên 50k, 200k, 800k dòng, ba lần/mức, cùng thiết bị đã khai báo.
- Tách warm-up/compile khỏi steady-state; lưu cả hai.
- Fit log–log và dự báo tới kích thước Pool B.
- Trần selector là 3 giờ; vượt thì thử shard chung, vẫn vượt thì TIMEOUT.

### 12.2. Gia cố mã mẫu `fit_scaling/gate_decision`

Mã review dùng point estimate là chưa đủ cho production. Bổ sung:

- metadata CPU/GPU/RAM/VRAM, thread, tải hệ thống;
- từng replicate, warm-up và outlier policy khai báo trước;
- slope, intercept, residual, interval dự báo;
- quyết định theo upper prediction bound thay vì chỉ point estimate;
- RSS model có đơn vị byte/GiB;
- fallback khi fit không ổn: chạy thêm point hoặc smoke shard, không dùng operations để loại.

Không tự đặt ngưỡng goodness-of-fit mới mà chưa ghi trong protocol; ngưỡng này cần
xác nhận khi triển khai calibration.

### 12.3. Evidence

`resource_calibration.parquet` và `resource_decision.json` chứa selector, device,
n, budget, replicate, warmup, seconds, RSS, VRAM, model, prediction và status.

## 13. SKQ-PC

### 13.1. Contract bắt buộc

1. Input là Pool B.
2. Tầng `g=(phase, class)`, tối đa 12 tầng có dữ liệu.
3. Budget largest remainder theo `|P_g|`, tối thiểu 1 nếu khả thi.
4. Anchor farthest-first trong từng tầng.
5. Voronoi cell trong tầng.
6. RFF RBF, sigma theo median heuristic train-only.
7. Chọn điểm trong cell theo candidate.
8. Simplex-QP trong tầng nếu candidate dùng QP.
9. `w_j=|P_g|p_j`, bảo toàn mass tầng.
10. Exact budget, unique indices, không proxy/fallback im lặng.
11. Bộ bọc shard là infrastructure chung, không là novelty.

### 13.2. Tối đa ba candidate active

Theo review, tổng số candidate dùng chọn dev là tối đa ba, không phải ba cộng thêm.

Danh sách mặc định từ review:

| Candidate | Cơ chế |
|---|---|
| A | SKQ-PC chuẩn: herding trong cell + QP |
| B | SKQ-PC + LRQ-SQ, alpha 0.5, OOF LR train-only |
| C | SKQ-PC-R: random trong cell, giữ quota/cell/QP |

Chọn bằng UL dev, XGBoost đã tune, seed 11/29/47 tại `rho*`. Nếu chênh dưới
0,002, chọn bản rẻ hơn. Không dùng CQ_med test cũ làm căn cứ.

### 13.3. Candidate CoreTab multiclass do nhóm đề xuất — `PENDING_APPROVAL`

Nhóm muốn thử một biến thể duy nhất có nền CoreTab và hỗ trợ multiclass. Điều này
không được tự động thêm thành candidate thứ tư vì QĐ2 yêu cầu dừng biến thể mới.

Đề xuất xin giảng viên xác nhận:

```text
SKQ-PC/CoreTab-cell:
  dùng multiclass XGBoost leaf signatures để tạo cell chung;
  vẫn stratify phase × class;
  phân bổ quota phase × class × cell;
  chọn đại diện trong cell;
  gán trọng số bảo toàn mass;
  không gọi là CoreTab native;
  không dùng OVA union;
  không thêm thành phương pháp thứ hai trong bài.
```

Hai lựa chọn hợp lệ:

- **Khuyến nghị:** thay candidate B hoặc C bằng CoreTab-cell trước mọi run CQ v1,
  vẫn giữ tổng cộng ba candidate; ghi preregistration/deviation được duyệt.
- Nếu không được duyệt: giữ ở nhánh exploratory sau M1, dev-only, không mở test,
  không tạo claim trong bài/luận văn chính.

Không triển khai candidate này trước khi có câu trả lời. Chỉ đổi binary objective
sang `multi:softprob` hoặc bọc OVA không đủ để claim phương pháp mới.

### 13.4. Test riêng nếu được duyệt

- multiclass 3 lớp không gọi binary native subset;
- exact budget và unique indices;
- phase × class mass preservation;
- leaf-cell quota hợp lệ;
- hoán vị label ID không làm thay đổi contract;
- ablation với SKQ-PC chuẩn, C03 và CoreTab OVA;
- runtime/RSS theo QĐ16;
- prior-art/novelty table trước claim.

## 14. CoreTab-XGB OVA adapted QĐ14

### 14.1. Contract

1. Mỗi lớp chạy CoreTab-XGB binary class-vs-rest ở upstream commit khóa.
2. Quota class dùng largest remainder theo prior Pool B tại tổng budget `m`.
3. Chỉ lấy positive rows của nhánh class đó, tối đa quota.
4. Union unique; không pad, không duplicate.
5. Thiếu positive rows thì `realized < requested`.
6. Seed khác nhau theo lớp nhưng được suy ra xác định từ selector seed.
7. Log CoreTab params, quota, positive returned và realized mỗi lớp.
8. Label chính xác: `CoreTab-XGB (OVA, adapted)`.

### 14.2. Gia cố `ovr_union_select` mẫu

- Tách rõ requested binary output size và positive quota.
- Map indices từ adapter về Pool B an toàn.
- Không giả định CoreTab luôn trả đủ positive rows.
- Không tune `sample_percent/examples_to_keep` trên test.
- Các cấu hình CoreTab tối đa ba trên dev như baseline khác.

### 14.3. Evidence

`coretab_ova_diagnostics.json`: upstream commit, class seed, params, quota,
returned positives, realized rows, duplicates removed và runtime.

## 15. Baseline và tái lập source

Mỗi baseline có manifest:

```text
method_id, paper, venue/rank source, upstream_url, upstream_commit,
fidelity_tier, declared_patches, task_contract, budget_contract,
toy_reproduction, CQ adaptation, limitations
```

Sáu baseline cần hoàn thiện: C01, C03, Moderate-DS, CCS, Data-OOB,
Kernel thinning/Compress++. Không tự thay bằng proxy nếu source/dependency lỗi.

CCS dùng OOF XGBoost difficulty và phải ghi adapted. Kernel thinning/Compress++
phải ghi rõ path thực thi. Facility location feature-space phải ghi adapted,
không ghi CRAIG native.

## 16. Headroom và ngân sách QĐ12

### 16.1. Chọn `rho*`

- FullTrain-B và C02 trên dev.
- `rho ∈ {0.5%, 1%, 2%, 5%}`.
- Ba seed 11/29/47.
- Learner XGBoost đã tune; weights đã mean-one.
- `delta(rho)=UL(FullTrain-B)-mean_seed UL(C02,rho)`.
- Chọn rho lớn nhất có `delta >= 0.01`; nếu không có, chọn 0.5%.
- Chỉ dùng FullTrain-B và C02; không dùng SKQ/baseline khác.

Nếu `rho* != 5%`, 5% chỉ là secondary descriptive budget.

### 16.2. Test và evidence

- Test reference `test_headroom_rule`.
- Kiểm tra missing seed, duplicate rho, invalid metric.
- `headroom_decision.json` ghi toàn bộ inputs, means, delta, rho*, commit/config.

## 17. Endpoint và thống kê

### 17.1. Endpoint

- UL: Macro-F1 cấp enrollment, trung bình P1–P4, test course mới.
- P1 Macro-F1: secondary endpoint đăng ký trước cho K3.
- EC: MAE của Q-hat course dùng PCC, trung bình P1–P4, khóa có `n_c >= n_min`.
- CC, course-equal weighting, signed error, TV distance, course Macro-F1: sensitivity/appendix.
- `n_min` và `delta_C` chốt tại M0 từ data card/dev, không đổi sau test.

### 17.2. Quy ước effect

Để tránh sai dấu:

```text
Delta_UL(A,B) = UL(A) - UL(B)        # dương có lợi cho A
Delta_EC(A,B) = EC(B) - EC(A)        # dương có lợi cho A vì EC thấp tốt
```

### 17.3. Giả thuyết

| ID | So sánh | H0 | H1 |
|---|---|---|---|
| K1 | SKQ-PC vs baseline mạnh nhất | Delta_UL <= 0 | Delta_UL > 0 |
| K2 | SKQ-PC vs C03 | Delta_UL <= 0 | Delta_UL > 0 |
| K3 | SKQ-PC vs A2 | Delta_UL <= 0 | Delta_UL > 0 |
| K4 | SKQ-PC vs A4 | Delta_UL <= 0 | Delta_UL > 0 |
| K5 | SKQ-PC vs FullTrain-B | Delta_UL <= -0.005 | Delta_UL > -0.005 |
| K1c–K4c | Tương ứng trên EC | Delta_EC <= 0 | Delta_EC > 0 |
| K5c | SKQ-PC vs FullTrain-B | Delta_EC <= -delta_C | Delta_EC > -delta_C |

### 17.4. Kiểm định

- Alpha 0.05, một phía.
- Paired course bootstrap 2.000 lần.
- Group resampling là `course_root_id` nếu có nhiều lần mở.
- Cùng bootstrap sample cho mọi method trong một comparison.
- Holm riêng cho K1–K5 và K1c–K5c.
- Báo effect, mean ± SD qua seed, CI hai phía, lower bound một phía,
  raw p, Holm-adjusted p, reject/not-reject và missing/failed runs.
- Không bỏ failed/timeout khỏi mẫu số.

### 17.5. Tiêu chí S1–S4

- S1: K1 đạt.
- S2: K3 đạt và A2 làm lệch phase mass tại P1 > 0.05.
- S3: K5 đạt hoặc `R_break <= 23`.
- S4 phụ: K5c đạt.

Nếu không đạt, định vị theo QĐ5; không đổi hypothesis/margin.

## 18. Freeze, deviation và test access

### 18.1. State machine

```text
DEV_OPEN
  -> M0_PROTOCOL_FROZEN
  -> DEV_SELECTION
  -> M1_METHOD_FROZEN
  -> TEST_UNLOCKED_ONCE
  -> CONFIRMATORY_COMPLETE
```

### 18.2. M0 khóa

- split strategy/hash;
- rho*;
- class weight policy;
- learner grid/winner;
- `n_min`, `delta_C`;
- shard size;
- resource decision rule;
- candidate list tối đa ba;
- selector/model seeds;
- feature schema.

### 18.3. M1 khóa

- SKQ-PC winner và selection evidence;
- baseline mạnh nhất trên dev;
- method/config list cho bài;
- extension list cho luận văn;
- code commit, config hash, split hash, dataset fingerprint;
- stats protocol;
- public/private artifact policy.

### 18.4. Manifest v4

Nâng `experiments/freeze.py`, runner validation và
`docs/freeze_manifest.example.json`. Không giữ example Adult/P02/P05 như mẫu CQ v1.

Schema tối thiểu:

```text
schema_version, manifest_id, previous_manifest_id,
plan_version, review_hashes, code_commit, config_hash,
dataset_fingerprints, split_hash, feature_schema_hash,
selector_seeds, model_seed, rho_star, class_weight_policy,
learner_params, early_stopping_policy, shard_policy,
method_roles, candidate_list, selected_candidate,
selection_evidence_hash, stats_protocol_hash,
allowed_extensions, test_access_policy, deviations
```

### 18.5. Deviation

- Manifest cũ bất biến.
- Thay đổi tạo version mới liên kết `previous_manifest_id`.
- Ghi lý do, người duyệt, thời điểm, phạm vi ảnh hưởng.
- Nếu thay protocol sau khi test đã mở, kết quả mới mặc định exploratory.

## 19. Artifact, traceability và Claim Ledger

### 19.1. Traceability schema có version

```text
traceability_schema_version, plan_version, requirement_id,
review_date, review_locator, superseded_by,
existing_file, existing_symbol, target_file, target_symbol,
test_ids, gate_id, evidence_id, evidence_visibility,
commit, run_ids, status, blocker, allowed_claim
```

### 19.2. Evidence ID

Mỗi evidence có ID ổn định, ví dụ `EV-QD15-WEIGHTS-001`, và manifest:

```text
evidence_id, requirement_ids, created_at, code_commit,
config_hash, split_hash, run_ids, artifact_sha256,
visibility, producer_command, status
```

Public chỉ chứa schema, manifest và hash; private location chứa row-level artifact.

### 19.3. Claim Ledger

```text
claim_id
→ requirement IDs
→ table/figure cell
→ runs_long row keys
→ run_ids
→ config/split/commit
→ evidence IDs
→ raw/private artifact hashes
```

Không có claim nào chỉ trỏ tới một file báo cáo thủ công.

### 19.4. Predictions schema private

```text
run_id, course_id, course_root_id, learner_id,
phase, p_E, p_G, p_A, y, split, seed, learner_id/model_id
```

## 20. Privacy audit QĐ17

### 20.1. Checklist

1. `git ls-files` không chứa dữ liệu CQ, predictions, indices, sample weights,
   row IDs, notebook output hoặc credentials.
2. Scan lịch sử Git object để phát hiện file nhạy cảm từng commit nhầm.
3. Scan archive public trước khi đóng gói.
4. Kiểm tra `.gitignore` và public allowlist.
5. Kiểm tra config không chứa token, private URL hoặc path làm lộ tên dữ liệu nhạy cảm.
6. Kaggle dataset/notebook Private và share trực tiếp giảng viên.
7. Public chỉ có code, schema, manifest, hash và aggregate không nhận diện dòng.
8. Nếu từng lộ dữ liệu, lập incident/deviation; không âm thầm xóa lịch sử.

### 20.2. Evidence

`privacy_audit.json`: commit, scanner version, tracked findings, history findings,
archive findings, allowlist, denylist, resolution và người kiểm tra.

## 21. Xử lý mã tham chiếu ở cuối Mục 7/phụ lục

### 21.1. Review 12 — Phụ lục E

| Nhóm hàm | Nơi production dự kiến | Cách dùng |
|---|---|---|
| `temporal_course_split`, `temporal_overlap_report`, `assert_disjoint_groups` | `data/cq_protocol.py` | Chuyển thành hàm có schema validation và artifact |
| `id_only_probe` | `data/cq_protocol.py` hoặc diagnostics | Train-only/dev-only, lưu aggregate |
| `loqv`, `quality_class`, `learner_index` | `data/cq_protocol.py` | Công thức chuẩn; scale phải explicit |
| `course_quality`, `class_conditional_means` | `training/course_metrics.py` | Tính train constants và Qc/Yc |
| `course_estimates`, PCC/CC | `training/course_metrics.py` | PCC chính, CC sensitivity |
| `course_level_errors`, `oracle_floor`, `icc1` | course metrics | Unit test và data-card evidence |
| `phase_cutoffs` | CQ adapter/protocol | Kiểm tra timestamp/cutoff |
| `paired_course_bootstrap*`, `holm` | `training/statistics.py` | Khóa signs, alpha, seed, group |
| `stratified_mass_preserving_sample` | `methods/controls.py` | C03 exact budget |
| mass/prior diagnostics, `prior_correct` | diagnostics/course metrics | A8 và H3d |

Không đặt toàn bộ mã phụ lục vào một file khổng lồ. Chia theo ownership, dùng type
validation, docstring tiếng Việt ngắn gọn và test production.

### 21.2. Review 13 — `cq_patch_1013.py`

| Hàm/patch | Quyết định |
|---|---|
| `normalize_training_weights` | Áp dụng công thức, nhưng hợp nhất vào helper hiện có và mọi run type |
| `effective_prior` | Áp dụng; input là effective weights |
| `selector_view` | Áp dụng ý tưởng, thay name-list bằng semantic schema |
| `enrollment_table` | Áp dụng aggregation; bỏ auto-guess scale trong production |
| `headroom_budget` | Áp dụng đúng QĐ12; thêm validation/evidence |
| `fit_scaling` | Áp dụng log–log nhưng thêm replicates/uncertainty/hardware |
| `gate_decision` | Không dùng point estimate đơn; thêm prediction interval/RSS |
| `largest_remainder` | Dùng helper chung, test tie/determinism |
| `ovr_union_select` | Áp dụng contract QĐ14; gia cố mapping/quota/diagnostics |
| patch `weights.py` | Áp dụng theo symbol, không theo line number |
| patch `evaluator.py` | Mở rộng selection/generated/full train; XGB wrapper đúng API |
| patch `runner.py` | Truyền dev, không test; selector/learner views tách nhưng indices thẳng hàng |

### 21.3. Bảy test review 13

Các test sau phải được port và đổi import sang package production:

1. `test_xgb_depends_on_weight_scale_until_normalized`.
2. `test_normalization_keeps_prior_and_mean_one`.
3. `test_selector_view_drops_id_columns`.
4. `test_enrollment_table_mean_over_chapters_and_labels_vary_within_course`.
5. `test_headroom_rule`.
6. `test_scaling_gate_recovers_slope`.
7. `test_ovr_union_quota_disjoint_no_padding`.

Các test mẫu là mức tối thiểu, không thay thế edge tests và integration tests trong
các mục tương ứng.

## 22. Encoding và quy ước code

- Python source và Markdown dùng UTF-8 không BOM.
- Thêm `.editorconfig` với `charset = utf-8`, LF cho source nếu phù hợp công cụ.
- CI/test đọc toàn bộ `.py/.md/.json` bằng UTF-8 và chạy `compileall`.
- Docstring tiếng Việt mô tả: mục đích, contract, fidelity/status, input/output,
  failure behavior và requirement ID trực tiếp; không chép cả review vào code.
- Tên symbol/code bằng tiếng Anh nhất quán; giải thích người dùng bằng tiếng Việt.
- Không dùng emoji trong machine-readable log/schema.

## 23. Quality gates

| Gate | Điều kiện đạt | Evidence | Khi fail |
|---|---|---|---|
| G00 Scope | Config không gọi retired/synthetic ngoài phạm vi | config audit | Chặn run |
| G01 Privacy | Không có banned artifact/secret tracked hoặc archive | privacy audit | Chặn push/release |
| G02 Data schema | CQ v1 đúng enrollment/schema | D01/D09/D10 | Dừng |
| G03 Split | Group disjoint, decision M0 có hash | split evidence | Dừng |
| G04 Labels | q/y/Qc/mu/ICC checks đạt | D09–D12 | Dừng |
| G05 Cutoff | 20 manual cases đạt | D06 evidence | Dừng snapshot |
| G06 Weights | Mean-one và contract tests đạt | pytest + run summary | Chặn train |
| G07 Views | ID/target không vào selector | tests + schema | Chặn selector |
| G08 Learner | Tune/early stop dev-only | spy tests + frozen params | Chặn confirmatory |
| G09 Resource | Có 3×3 measurements, decision traceable | calibration evidence | Run/shard/TIMEOUT |
| G10 Fidelity | Upstream commit/patch/toy evidence | method manifest | Không đưa bảng chính |
| G11 SKQ-PC | Exact budget/mass/cell/QP tests | contract tests | Không cho candidate |
| G12 CoreTab OVA | Quota/no-pad/realized tests | OVA diagnostics | Không đưa bảng chính |
| G13 Stats | Hypothesis/sign/alpha/Holm frozen | stats protocol hash | Chỉ descriptive |
| G14 Freeze M0 | Protocol fields đủ | manifest validation | Không dev selection |
| G15 Freeze M1 | Winner/extensions/evidence đủ | manifest validation | Không mở test |
| G16 Reporting | Mọi số truy được run/evidence | Claim Ledger audit | Không xuất bài |

## 24. File map chi tiết

### 24.1. File hiện có phải sửa

```text
.gitignore
pyproject.toml
src/skq_exp/config.py
src/skq_exp/resources.py
src/skq_exp/data/registry.py
src/skq_exp/data/adapters/course_quality.py
src/skq_exp/experiments/freeze.py
src/skq_exp/experiments/provenance.py
src/skq_exp/experiments/runner.py
src/skq_exp/methods/contracts.py
src/skq_exp/methods/controls.py
src/skq_exp/methods/registry.py
src/skq_exp/methods/native/coretab.py
src/skq_exp/methods/proposed/structured_kquad.py
src/skq_exp/training/weights.py
src/skq_exp/training/evaluator.py
src/skq_exp/training/learners.py
src/skq_exp/training/metrics.py
src/skq_exp/reports/aggregate.py
src/skq_exp/reports/archive.py
docs/freeze_manifest.example.json
docs/IMPLEMENTATION_STATUS.md
docs/DATASET_ADAPTERS.md
```

### 24.2. File dự kiến thêm

```text
.editorconfig
docs/REVIEW_TRACEABILITY_2026-10-12_13.md
docs/CQ_V1_DATA_CARD_TEMPLATE.md
docs/METHOD_FIDELITY_REGISTRY.md
docs/CLAIM_LEDGER.md
src/skq_exp/data/cq_protocol.py
src/skq_exp/data/adapters/course_quality_v1.py
src/skq_exp/experiments/resource_calibration.py
src/skq_exp/methods/adapted/__init__.py
src/skq_exp/methods/adapted/coretab_ova.py
src/skq_exp/methods/proposed/skq_pc.py
src/skq_exp/training/course_metrics.py
src/skq_exp/training/statistics.py
scripts/audit_public_release.py
tests/test_cq_protocol.py
tests/test_cq_patch_1013_contracts.py
tests/test_course_quality_v1_adapter.py
tests/test_method_fidelity.py
tests/test_privacy_audit.py
tests/test_resource_calibration.py
tests/test_skq_pc.py
tests/test_coretab_ova.py
tests/test_course_metrics.py
tests/test_statistics.py
```

Tên file cuối cùng có thể điều chỉnh để tránh trùng module, nhưng mọi thay đổi phải
cập nhật ma trận traceability trước khi code.

## 25. Timeline, owner, Plan B và rollback

### 25.1. Timeline khôi phục từ review

| Ngày | P0 bắt buộc | Sản phẩm | Owner |
|---|---|---|---|
| 14/10 | Xác nhận Private, tài nguyên, owner; báo cáo nhanh `enrollment_table` | checklist + 1 trang thống kê | Nhóm điền |
| 14–16/10 | QĐ15, O16, O17, predictions schema, mã phụ lục/test | PR kiểm thử | Nhóm phương pháp |
| 14–17/10 | CQ v1, Pool B, split, data card | data card, split hash | Nhóm dữ liệu |
| 14–19/10 | Sáu baseline + CoreTab OVA | code + toy tests | Nhóm phương pháp |
| 17–19/10 | Resource calibration 10 selector + 3 candidate | bảng time/RSS | Nhóm phương pháp |
| 18–20/10 | FullTrain-A/B dev, weights policy, headroom, D01–D12 | UL/EC dev, rho* | Cả nhóm |
| 19–21/10 | Khung bài, đề cương, BibTeX, novelty table | tài liệu M0 | Cả nhóm |
| 21/10 | M0 GO/NO-GO | protocol freeze | Giảng viên duyệt |
| 22–25/10 nếu GO | Dev selection tối đa 3 candidate | winner evidence | Nhóm phương pháp |
| 25/10 | M1 GO branch | freeze manifest v4 | Giảng viên duyệt |
| 26–28/10 | Mở test một lần và sinh bảng | confirmatory artifacts | Nhóm phương pháp |
| 29–31/10 | Viết/sửa/nộp nếu GO | bài nộp | Cả nhóm |
| 08/11 nếu NO-GO | M1 luận văn | freeze luận văn | Giảng viên duyệt |
| đến 06/12 | GĐ2 luận văn | 5 seed/extensions | Cả nhóm |

### 25.2. Ưu tiên

- **P0 đường găng:** privacy, CQ v1/data card/split, weights, selector view,
  early stopping, resource calibration, endpoints, controls, freeze.
- **P1 trước M1:** baseline reproduction, SKQ-PC, CoreTab OVA, stats/reporting.
- **P2 sau GO/freeze:** extra learners, Adult/Covertype, RQ5, extended ablations.
- **Không làm GĐ0:** synthetic, chạy lại CatBoost pilot, thêm candidate thứ tư.

### 25.3. Plan B

| Rủi ro | Trigger | Plan B |
|---|---|---|
| CQ v1 chưa xong | Không có Pool B/data card 17/10 | Báo giảng viên, xét NO-GO |
| Không có event timestamp | Không dựng cutoff đúng | Báo trước 17/10; không tự dùng CQ_med làm CQ v1 |
| Temporal không đủ lực | timestamp/class count/CI fail | SGKF 5×2, khóa tại M0 |
| Temporal overlap cao | >5% | Thêm NOLFO sensitivity |
| Selector >3h | upper prediction bound >3h | Shard chung; vẫn vượt → TIMEOUT |
| Baseline source lỗi | toy reproduction fail | BLOCKED + evidence; không proxy |
| rho*=0.5% và methods gần nhau | headroom result | Kết luận ngân sách nhỏ đủ; QĐ5(c) nếu cần |
| SKQ không hơn C03 | dev result | Thu hẹp claim về stratification/control |
| SKQ không hơn baseline | dev result | Benchmark/empirical study theo QĐ5(c) |
| Test run hỏng kỹ thuật | artifact cho thấy infrastructure failure | Không đổi method; dùng rerun policy đã freeze/deviation |

### 25.4. Rollback

- Mỗi workstream là commit nhỏ có test.
- Rollback code bằng `git revert`, không reset/force-push.
- Feature mới chỉ bật qua config mới; config pilot cũ vẫn tái lập được.
- Migration schema có version; reader hỗ trợ manifest cũ ở chế độ historical.
- Dataset/split/artifact không ghi đè; version/hash mới và deviation.
- Tag review/freeze bất biến.
- Nếu PR gây regression, revert commit hẹp nhất và giữ evidence lỗi.

## 26. Kế hoạch commit sau khi kế hoạch được duyệt

| # | Commit | Gate hoàn thành | Rollback scope |
|---:|---|---|---|
| 1 | Add V2 traceability, taxonomy and encoding rules | G00 | docs only |
| 2 | Add public release privacy audit | G01 | audit/release only |
| 3 | Normalize effective weights for every run type | G06 | training weights |
| 4 | Separate selector and learner views | G07 | view/schema |
| 5 | Enable dev-only tuning and early stopping | G08 | learner/evaluator |
| 6 | Replace operation gate with measured calibration | G09 | resources |
| 7 | Add CQ enrollment/schema protocol | G02/G04 | data protocol |
| 8 | Add split decision and snapshots | G03/G05 | split/snapshot |
| 9 | Add course endpoints and prediction schema | G04 | metrics/artifacts |
| 10 | Add C01/C03 and fixed baselines | G10 | baseline modules |
| 11 | Add SKQ-PC candidates (max 3 approved) | G11 | proposed module |
| 12 | Add CoreTab OVA adapted | G12 | adapted module |
| 13 | Add bootstrap/Holm/headroom | G13 | statistics |
| 14 | Upgrade freeze/deviation state machine | G14/G15 | freeze/runner |
| 15 | Add reports, evidence manifest and Claim Ledger | G16 | reports/docs |
| 16 | Add M0 configs and dry-run | G00–G14 | configs |
| 17 | Full verification/privacy regression | all pre-M1 | tests only |
| 18 | Update docs and open PR without squash | review checklist | docs/release |

Không bắt đầu commit 11 cho CoreTab-cell nếu câu hỏi ở Mục 27 chưa được duyệt.

## 27. Câu hỏi bắt buộc xác nhận

1. Có cho phép **thay một trong ba candidate SKQ-PC** bằng
   `SKQ-PC/CoreTab-cell` hay phải giữ đúng A/B/C của review?
2. Nếu cho phép, candidate nào bị thay: LRQ-SQ hay random-in-cell?
3. Có chấp nhận `CoreTab-cell` là candidate nội bộ dưới tên SKQ-PC, không phải
   phương pháp mới/không phải CoreTab native?
4. Ngưỡng timestamp “đáng tin cậy” cần định nghĩa theo missing rate nào?
5. Xác nhận tiêu chí fallback: test <10 khóa/lớp hoặc CI half-width >0.005.
6. Xác nhận `n_min` và `delta_C` tại M0.
7. Xác nhận policy rerun khi lỗi hạ tầng sau khi test đã mở.
8. Chỉ định owner nhóm dữ liệu, nhóm phương pháp và người duyệt privacy/freeze.

## 28. Acceptance checklist của chính kế hoạch V2

- [ ] Mọi QĐ1–QĐ17 có requirement row.
- [ ] R1–R2, O1–O18, Y1–Y16 được xử lý hoặc ghi lý do ngoài scope.
- [ ] Mã phụ lục review 12/13 có quyết định tích hợp cụ thể.
- [ ] Mọi file đích khớp cấu trúc repo hoặc được ghi rõ là file mới.
- [ ] Temporal/SGKF/NOLFO không còn nhập nhằng.
- [ ] Có timeline, owner placeholder, dependency, Plan B và rollback.
- [ ] Có taxonomy native/adapted/binary/proposed và test tương ứng.
- [ ] Có gate, pass criterion, evidence và fail action.
- [ ] Có workflow dev → M0 → M1 → test và deviation.
- [ ] Có H0/H1, alpha, sign, Holm và report schema.
- [ ] Traceability/Claim Ledger có version, run_id và evidence ID.
- [ ] Privacy audit bao phủ working tree, Git history và archive.
- [ ] Candidate CoreTab multiclass không làm tổng candidate vượt ba khi chưa duyệt.
- [ ] Không có hành động triển khai nào được ngầm cho phép trước khi nhóm xác nhận.

## 29. Điều kiện bắt đầu triển khai

Chỉ bắt đầu sửa code khi:

1. Nhóm duyệt bản V2 này.
2. Nhóm trả lời các câu hỏi có thể tự quyết ở Mục 27.
3. Câu hỏi CoreTab-cell được gửi giảng viên nếu nhóm muốn thay candidate.
4. Owner được điền.
5. Nhánh triển khai và commit nền được xác nhận.

Sau đó thực hiện tuần tự theo commit plan, mỗi commit phải qua gate tương ứng trước
khi chuyển sang commit phụ thuộc tiếp theo.
