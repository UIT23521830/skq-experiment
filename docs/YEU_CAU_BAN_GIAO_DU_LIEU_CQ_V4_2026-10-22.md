# Yêu cầu bàn giao dữ liệu CQ V4

**Ngày lập:** 22/10/2026
**Mục tiêu:** hoàn thành đầu vào dữ liệu theo Review-2026-10-22 để nhóm thực nghiệm có thể chạy M0-V4 trên train/dev ngay khi nhận bàn giao, không phải yêu cầu bổ sung schema hoặc chia lại dữ liệu.
**Mức ưu tiên:** P0, nằm trên đường găng của điểm kiểm tra M0-V4 ngày 29/10 và kế hoạch viết bài.

## 1. Kết quả cần bàn giao

Nhóm dữ liệu cần bàn giao một phiên bản bất biến mang tên **CQ V4**. V4 kế thừa bộ lọc, target và đặc trưng của V3, nhưng thay toàn bộ cách chia theo `course_id` bằng cách chia theo **họ khóa học** (`course_family_id`) theo QĐ19.

Gói bàn giao phải cho phép nhóm thực nghiệm thực hiện ngay:

1. kiểm tra tính toàn vẹn, schema và hash;
2. xác nhận không giao họ khóa giữa train, dev và test;
3. dựng Pool B train và bốn tập dev P1–P4;
4. chạy FullTrain-A tại `lambda = 1` trên đúng cohort train V4;
5. chạy FullTrain-B, headroom, QĐ16 và panel SKQ-PC trên dev;
6. giữ test khóa, không để notebook dev đọc feature hoặc label test;
7. tái tạo được dữ liệu từ mã nguồn và manifest đi kèm.

## Bảng truy vết yêu cầu review và công việc nhóm dữ liệu

Bảng này dùng để trả lời trực tiếp câu hỏi: **yêu cầu nào của giảng viên dẫn đến công việc dữ liệu nào, sản phẩm nào chứng minh đã làm và điều kiện nào mới được xem là đạt**. Mã QĐ, R, O và Y giữ nguyên theo Review-2026-10-22.

| Mã review | Yêu cầu/nhận xét của giảng viên | Công việc nhóm dữ liệu phải làm | Sản phẩm chứng minh | Điều kiện nghiệm thu | Ưu tiên |
|---|---|---|---|---|---|
| **QĐ18** | Không mở test trước freeze M1; tiếp tục train/dev đến điểm kiểm tra M0-V4 | Tách test thành gói riêng; runtime bundle M0-V4 chỉ chứa train và dev; không để preprocessing hoặc notebook dev đọc test | `README_HANDOFF.md`, manifest dev-only, validation `test_excluded=true` | Dev bundle không có test feature/label; hash và manifest chứng minh phạm vi file | P0 |
| **QĐ19 / R3** | Không dùng `course_id` làm đơn vị nhóm; phải tạo `course_family_id` để ngăn lần mở lại cùng nội dung đi qua nhiều split | Tạo họ khóa bằng connected components của Jaccard ccid ≥ 0,9; khóa có dưới 5 ccid/không có ccid là singleton; chạy sensitivity 0,8 | `course_family_members.parquet`, `course_family_summary.parquet`, `COURSE_FAMILY_SENSITIVITY.md` | Mỗi course thuộc đúng một family; kết quả tất định; có thống kê 0,8 và 0,9 | P0.1 |
| **QĐ19 / R3** | Test phải là các họ khóa mở muộn; train/dev chia ở cấp họ khóa | 20% family mở muộn nhất làm test; 80% còn lại chia train/dev 70:10, seed 42, stratify theo quartile `n_enroll_labeled × has_E` | `family_splits.parquet`, `course_splits.parquet`, `splits.json` | Không family/course/enrollment leakage; số family test đúng `ceil(20%)`; chạy lại cho cùng hash | P0.2 |
| **QĐ19, Mục 7.3a** | Phải báo temporal overlap; nếu >5% thì chuẩn bị cho NOLFO | Tính tỷ lệ family train còn hoạt động sau thời điểm family test sớm nhất; lưu danh sách family overlap | Data card V4, `temporal_overlap.json` hoặc trường tương đương trong validation | Có tử số, mẫu số, tỷ lệ và danh sách family; cờ `requires_nolfo` khi >5% | P0.2 |
| **O20** | Dev V1 bị một khóa chi phối và lực thống kê yếu | Khi chia dev, stratify theo cỡ family và `has_E`; báo tỷ trọng khóa lớn nhất và số khóa hiệu dụng | Data card V4, `concentration` trong summary/validation | Có `largest_share`, `effective_courses`, `n_courses` riêng cho dev và test | P0.2 |
| **O20 / QĐ21** | So sánh và CI phải cluster theo họ khóa | Giữ `course_family_id` trong metadata của mọi dòng train/dev và bảo đảm ánh xạ thẳng hàng với row ID | Parquet metadata hoặc cột metadata trong Pool B; schema/validation | 100% row có family ID hợp lệ; family ID không lọt vào feature matrix | P0.3 |
| **O21 / QĐ20** | Lớp E gần biến mất ở ρ*=0,5%; ứng viên mới dùng phân bổ căn bậc hai | Không oversample hoặc đổi prior trong dữ liệu chính; bảo toàn đầy đủ lớp E; xuất capacity chính xác của 12 tầng `phase × class` | Thống kê phase-class trong Data Card/summary; Pool B có `phase` và `y_alpha_1` | Count E/G/A theo từng phase/split khớp Parquet; không mất lớp do builder | P0.3 |
| **QĐ20** | SKQ-PC-√ và C03 phải dùng cùng quota | Nhóm dữ liệu chỉ cần cung cấp capacity, phase, class, row ID ổn định; không tự cài selector hoặc thay quota trong data | Metadata train và validation phase-class | Mỗi train row có `phase`, target và row ID; tổng capacity khớp Pool B | P0.3 |
| **QĐ21** | Target chính là `y_alpha_1`; trọng số lớp tự nhiên; `Qc`, `nc` chỉ tính trên enrollment có nhãn | Đặt `y_alpha_1` làm target chính; ghi `y_alpha_0p1` là sensitivity-only; xuất khóa/course counts chỉ trên enrollment có nhãn | Data card V4, target manifest, summary theo split | Không trộn target; count `nc`, `Qc`, E/G/A dùng đúng mẫu số có nhãn | P0.3 |
| **QĐ21** | Giữ `nmin=30`, `delta_C=0,01`; cần biết số khóa đủ điều kiện EC | Báo phân bố `nc`, số khóa/family dev và test có `nc ≥ 30`, sàn EC dev và signed deviation fields cần thiết | Data card V4, course-level summary | Có mẫu số, số khóa đủ điều kiện và cách tính tái lập được | P1 |
| **QĐ21 / QĐ12** | Headroom phải chạy lại trên V4 với 5 seed C02 | Dữ liệu phải cung cấp đúng một train pool và cùng bốn dev phase cho mọi seed; không tạo split khác theo seed | Pool B V4 bất biến, split/hash | Mọi seed dùng cùng data hash/split; khác biệt chỉ ở selector seed | P0.3 |
| **QĐ22 / O23** | FullTrain-A là snapshot `lambda=1` của khóa train, không phải P4=0,9 | Chạy cùng builder ở `lambda=1`; tạo đúng một dòng mỗi enrollment train; đối chiếu cohort với Pool B train | `fulltrain_a/train.parquet`, validation, feature/preprocessing manifest | Enrollment A và B train khớp cohort; không có dòng dev/test; không gọi P4 là A | P0.4 |
| **O17** | Selector và learner phải dùng hai biểu diễn khác nhau | Xuất hai allowlist; selector không có ID, learner có đúng cột danh mục đã duyệt; metadata tách khỏi feature matrix | `selector_feature_columns.json`, `learner_feature_columns.json`, `feature_dictionary.json` | Không có ID/split/target trong selector view; thứ tự feature cố định và có hash | P0.3 |
| **O24** | Data card chưa ghi căn cứ, phiên bản nhãn và khác biệt với LoDiBi/TEMPO-DQ | Bổ sung căn cứ công thức, phiên bản code/model, P95, sentiment, NULL, chapter `-1`; lập bảng ánh xạ đặc trưng | `DATA_CARD_V4.md`, bảng mapping TEMPO-DQ | Người đọc xác định được điểm giống/khác và tái tạo target; không gọi nhãn là nhãn chuyên gia | P1 |
| **QĐ23 / Y18** | Repo công khai; không được đưa dữ liệu dòng vào Git | Chỉ gửi Parquet qua Kaggle/Drive riêng; Git chỉ giữ schema, hash, data card, manifest không chứa dòng dữ liệu hoặc ID nhạy cảm | `README_HANDOFF.md`, allowlist commit | Không có Parquet/raw/predictions/row-level file trong commit Git | P0 |
| **Y20** | Tên V1/V2/V3 đang gây nhầm lẫn | Đặt version chính thức là `CQ V4`; mọi thư mục, manifest, archive và data card dùng cùng tên/version | `dataset_version` trong mọi manifest | Không còn archive mới ghi V1/V2/V3 cho sản phẩm V4 | P0 |
| **Kiểm tra 1–12 / Phụ lục A dòng 32–35** | Phải chạy lại probe/contract trên V4 | Xuất dữ liệu đủ cho ID probe, missingness, cutoff, shuffled-label/majority; chạy các check thuộc builder/data | `validation.json`, báo cáo checks | Mọi check bắt buộc có PASS/FAIL và bằng chứng; không chỉ ghi tổng PASS | P1 |
| **Mục 7.3f** | Mọi báo cáo phải ghi version, split, seed, learner, budget, cấp đánh giá và số khóa EC | Gắn version/split/family/phase vào metadata và manifest để nhóm thực nghiệm không phải suy đoán | Schema, manifest, course-level summary | Tất cả trường định danh giao thức có mặt và nhất quán | P0.3 |
| **Phụ lục A dòng 31 / RQ5** | Kịch bản đối tượng cũ 8:1:1 là phân tích GĐ2, không phải split chính V4 | Giữ đủ mapping user-course/family để có thể dựng kịch bản sau; chưa cần tạo hoặc chạy trong P0 nếu làm chậm V4 | Data dictionary và provenance | Metadata đủ nhưng không thay split chính QĐ19 | P2, sau M1 |

### Phân công để tránh giao nhầm việc

Các hạng mục dưới đây **không phải đầu ra chính của nhóm dữ liệu**, nhưng dữ liệu phải cung cấp đúng contract để nhóm thực nghiệm thực hiện:

| Yêu cầu review | Nhóm thực nghiệm/code chịu trách nhiệm | Nhóm dữ liệu hỗ trợ gì |
|---|---|---|
| **QĐ20** SKQ-PC-√, C03 cùng quota, chuyển SKQ-PC-R thành A3 | Cài allocator, selector, weights, config và unit test | Phase, class, capacity và row ID ổn định |
| **QĐ22 / O22** Kernel Thinning → Compress++ | Cài baseline, shard wrapper, fidelity và timeout | Không cần tạo dữ liệu riêng ngoài Pool B đúng schema |
| **QĐ16** đo 10 selector, CoreTab OVA và 3 ứng viên | Chạy benchmark, timing, RSS và dự báo | Cung cấp Pool B bất biến và thống kê kích thước |
| **O20/QĐ21** bootstrap CI, headroom 5 seed | Tính metric, CI và chọn `rho*` | Cung cấp `course_family_id`, khóa nhóm và split đúng |
| **Y21** tinh chỉnh LR | Chạy 8 cấu hình và kiểm tra hội tụ | Dữ liệu chuẩn hóa/feature order ổn định |
| **Y19** PR vào main và tag review | Nhóm code thực hiện | Không commit dữ liệu dòng; cung cấp hash/data card để tham chiếu |
| **Y17** BibTeX và novelty ledger | Nhóm viết bài thực hiện | Cung cấp trích dẫn/phương pháp nguồn cho nhãn và dữ liệu nếu có |

### Bảng kiểm phản hồi nhanh cho nhóm dữ liệu

Khi trả lời ETA, đề nghị nhóm dữ liệu điền trực tiếp bảng sau:

| Hạng mục | Mã review | Trạng thái `NOT_STARTED/RUNNING/DONE/BLOCKED` | ETA | Đường dẫn sản phẩm hoặc blocker |
|---|---|---|---|---|
| Family mapping Jaccard 0,9 | QĐ19/R3 |  |  |  |
| Sensitivity Jaccard 0,8 | QĐ19/Mục 7.3a |  |  |  |
| Family split và hash | QĐ19/R3 |  |  |  |
| Temporal overlap | QĐ19 |  |  |  |
| Pool B train/dev P1–P4 | O13/O17 |  |  |  |
| Preprocessing train-only | O17/Mục 7.3a |  |  |  |
| FullTrain-A `lambda=1` | QĐ22/O23 |  |  |  |
| Data card V4 và label mapping | O24 |  |  |  |
| Validation 1–12 | Mục 7.4/Phụ lục A |  |  |  |
| Dev-only bundle, test excluded | QĐ18 |  |  |  |
| Manifest và SHA-256 | Mục 7.4 |  |  |  |

## 2. Quy tắc bắt buộc tạo course family

### 2.1. Đầu vào

Tạo bảng ánh xạ `course_id -> course_family_id` từ bảng quan hệ `course_id`, `video_id`, `ccid` của toàn bộ **1.808 khóa có nhãn** trong V3.

- Với mỗi `course_id`, tạo tập `ccid` duy nhất.
- Chỉ so sánh/gộp hai khóa khi mỗi bên có ít nhất 5 `ccid`.
- Nối hai khóa khi Jaccard của hai tập `ccid` lớn hơn hoặc bằng `0,9`.
- Một họ khóa là một thành phần liên thông của đồ thị trên; quan hệ phải có tính bắc cầu.
- Khóa thiếu ánh xạ `ccid` hoặc có dưới 5 `ccid` được giữ thành họ một phần tử, không loại khỏi dữ liệu.
- `course_family_id` phải tất định. Khuyến nghị dùng `course_id` nhỏ nhất trong họ hoặc một hash ổn định từ danh sách thành viên đã sắp xếp.

### 2.2. Phân tích độ nhạy

Chạy lại phép tạo họ ở ngưỡng Jaccard `0,8` và báo cáo chênh lệch so với ngưỡng chính `0,9`:

- tổng số họ;
- số họ có từ hai khóa trở lên;
- số khóa đổi họ;
- phân bố kích thước họ;
- số họ/khóa lớn nhất;
- ảnh hưởng đến số mẫu và phân bố lớp ở mỗi split nếu áp dụng ngưỡng `0,8`.

Ngưỡng chính để tạo V4 vẫn là `0,9`; kết quả `0,8` chỉ là sensitivity analysis, không tự thay split chính.

### 2.3. File phải xuất

`course_family_members.parquet` cần tối thiểu các cột:

| Cột | Ý nghĩa |
|---|---|
| `course_id` | ID lần mở khóa hiện tại |
| `course_family_id` | ID họ khóa tất định |
| `n_ccid` | Số ccid duy nhất của khóa |
| `family_size_courses` | Số course_id trong họ |
| `family_min_course_start` | Ngày mở sớm nhất của họ |
| `family_max_course_end` | Ngày kết thúc muộn nhất của họ |
| `mapping_status` | `jaccard_component`, `singleton_no_ccid`, `singleton_lt5_ccid` hoặc trạng thái tương đương |

`course_family_summary.parquet` cần một dòng mỗi họ:

| Cột | Ý nghĩa |
|---|---|
| `course_family_id` | ID họ khóa |
| `family_start` | `min(course_start)` |
| `family_end` | `max(course_end)` |
| `n_courses` | Số course_id |
| `n_enroll_labeled` | Số lượt ghi danh có nhãn |
| `has_E` | Họ có ít nhất một lượt ghi danh lớp E của `y_alpha_1` |
| `n_E`, `n_G`, `n_A` | Số lượt ghi danh từng lớp |

Xuất thêm báo cáo `COURSE_FAMILY_SENSITIVITY.md` và, nếu thuận tiện, bảng cạnh `course_family_edges.parquet` chứa hai khóa, intersection, union và Jaccard để kiểm toán.

## 3. Quy tắc split V4

### 3.1. Test theo thời gian ở cấp họ khóa

1. Sắp xếp họ khóa theo `family_start`, sau đó theo `course_family_id` để phá hòa tất định.
2. Lấy `ceil(20% * số họ)` có ngày mở muộn nhất làm test.
3. Toàn bộ course và enrollment của một họ phải thuộc cùng một split.
4. Không cân bằng lại test theo lớp và không di chuyển thủ công họ khóa sau khi xem phân bố nhãn.

### 3.2. Train/dev trên phần còn lại

80% họ còn lại được chia thành train/dev theo tỷ lệ toàn bộ dữ liệu `70:10`, tương đương xác suất dev `0,1 / 0,8 = 0,125` trên phần còn lại.

- Seed cố định: `42`.
- Tầng phân chia: `quartile(n_enroll_labeled) x has_E`.
- Mỗi họ chỉ xuất hiện trong một split.
- Ghi rõ quy tắc xử lý tầng quá nhỏ và phá hòa.
- Không dùng split ngẫu nhiên theo user-course.
- Không dùng split ngẫu nhiên trực tiếp theo `course_id`.
- Không dùng StratifiedGroupKFold cho V4 chính.

### 3.3. File split và hash

Xuất đồng thời:

- `family_splits.parquet`: một dòng mỗi `course_family_id`, gồm split và các trường thống kê dùng để chia;
- `course_splits.parquet`: một dòng mỗi `course_id`, gồm `course_family_id` và split;
- `splits.json`: assignment tất định cùng seed, tham số, timestamp và SHA-256 của các bảng nguồn;
- `SHA256SUMS.txt`: hash của mọi Parquet/JSON/Markdown trong gói bàn giao;
- `run_manifest.json`: commit/script, môi trường, input version và output version.

`splits.json` phải được khóa và commit trước khi chạy mô hình. Không đổi split sau khi xem kết quả dev.

### 3.4. Kiểm tra split bắt buộc

| Kiểm tra | Điều kiện đạt |
|---|---|
| Family leakage | Giao của tập `course_family_id` giữa mọi cặp split bằng rỗng |
| Course leakage | Giao của `course_id` giữa mọi cặp split bằng rỗng |
| Enrollment leakage | Khóa `(user_id, course_id)` không lặp qua split |
| Phase consistency | Bốn phase của một enrollment có cùng split |
| FullTrain-A consistency | Enrollment train của A trùng cohort train của B |
| Tỷ lệ test | Đúng `ceil(20% * số họ)` |
| Thứ tự test | `min(family_start_test) >= max(family_start_non_test)` theo quy tắc QĐ19 |
| Reproducibility | Chạy lại cùng input/seed cho cùng assignment và hash |

## 4. Temporal overlap và phương án NOLFO

Tính:

```text
temporal_overlap = tỷ lệ họ train có family_end > min(family_start của test)
```

Báo cả tử số, mẫu số và danh sách họ overlap. Nếu `temporal_overlap > 5%`, phải đánh dấu rõ trong data card và chuẩn bị đủ metadata để nhóm thực nghiệm chạy thêm NOLFO cho FullTrain-B và ứng viên chốt ở giai đoạn luận văn. Không tự đổi split V4 chính nếu chưa có quyết định mới.

## 5. Pool B V4

### 5.1. Cohort và target

- Chỉ dùng các enrollment có nhãn sau bộ lọc V3.
- Target chính duy nhất cho panel: `y_alpha_1`.
- `y_alpha_0p1` không dùng trong bảng chính; nếu giữ thì ghi là sensitivity-only.
- Pool B gồm bốn snapshot tích lũy P1–P4 với `lambda = 0,25; 0,50; 0,75; 0,90`.
- Khóa duy nhất của snapshot: `(user_id, course_id, phase)` hoặc một `row_id` tất định ánh xạ được về khóa này.
- Mỗi enrollment supervised phải có đủ bốn phase; trường hợp thiếu phải được liệt kê và giải thích, không tự nhân bản dòng.

### 5.2. Hai biểu diễn

Giữ hai feature view đã thống nhất:

- **Selector view:** chỉ đặc trưng hành vi; không có cột mã định danh.
- **Learner view:** selector view cộng các cột danh mục đã duyệt.

Xuất rõ:

- `selector_feature_columns.json`;
- `learner_feature_columns.json`;
- `feature_dictionary.json`;
- bảng đối chiếu với tập đặc trưng TEMPO-DQ: `present`, `equivalent`, `new`, `missing`.

Không đưa `user_id`, `course_id`, `course_family_id`, split hoặc target vào ma trận selector. Các ID chỉ được giữ trong metadata để group/evaluate.

### 5.3. Tiền xử lý

- Fit encoder, imputer, scaler và mọi thống kê X **chỉ trên Pool B train V4**.
- Dùng chung một preprocessor cho P1–P4 và dev.
- Không fit riêng từng phase.
- Không đọc feature hoặc label test khi fit.
- Ghi categories, imputation values, scaling parameters, input/output column order và software version trong `preprocessing.json`/artifact tương đương.
- Reference P95 dùng để định nghĩa target phải được mô tả riêng, không nhầm với preprocessing của X.

### 5.4. Dữ liệu runtime dev-only

Gói gửi cho nhóm thực nghiệm trước M1 chỉ chứa:

- Pool B train V4;
- Pool B dev P1–P4;
- metadata train/dev cần cho group và endpoint;
- preprocessor fit trên train;
- split manifest có thể ghi danh sách family test, nhưng **không chứa feature hoặc label test**.

Test Parquet/label phải được giữ ở gói riêng, chưa mount vào notebook dev. Không tải test lên Kaggle notebook dùng cho M0-V4.

## 6. FullTrain-A V4

FullTrain-A không phải P4 và không được đổi tên P4 thành A.

Nhóm dữ liệu cần gọi cùng builder với:

```text
lambda = 1.0
cutoff = course_end
```

Yêu cầu:

- chỉ dựng snapshot `lambda=1` cho các enrollment có nhãn thuộc khóa/họ train V4;
- cohort, target, feature allowlist và preprocessing contract phải tương thích với FullTrain-B;
- mỗi enrollment train có đúng một dòng A;
- không đưa snapshot A vào Pool B bốn phase;
- nhóm thực nghiệm sẽ huấn luyện một mô hình FullTrain-A rồi đánh giá trên dev P1–P4 của Pool B;
- xuất báo cáo đối chiếu enrollment ID của FullTrain-A với train Pool B: thiếu, thừa và trùng phải đều bằng 0 hoặc được giải thích bằng văn bản.

File tối thiểu:

- `fulltrain_a/train.parquet`;
- `fulltrain_a/feature_columns.json`;
- `fulltrain_a/preprocessing.json` hoặc chỉ dẫn dùng preprocessor chung;
- `fulltrain_a/validation.json`;
- `fulltrain_a/run_manifest.json`.

## 7. Data card V4

Data card V4 phải kế thừa nội dung hữu ích của V3 và bổ sung các mục sau.

### 7.1. Căn cứ và phiên bản cách tính nhãn

Ghi rõ:

- nhãn là chất lượng vận hành được tính theo chuẩn/công thức đã công bố, không phải nhãn chuyên gia;
- `y_alpha_1` dùng đúng công thức LOQV đã chốt;
- nguồn và phiên bản code/model;
- khác biệt với công bố gốc: chuẩn hóa P95 thay min-max, mô hình sentiment, xử lý NULL, bucket chapter `-1` và mọi thay đổi khác;
- không diễn giải proxy hành vi thành năng lực hoặc chất lượng chuyên gia nếu chưa có bằng chứng;
- bảng ánh xạ nguồn/nhãn/đặc trưng với LoDiBi và TEMPO-DQ.

### 7.2. Thống kê bắt buộc

Báo theo từng split:

- số `course_family_id`, `course_id`, enrollment có nhãn và user;
- phân bố E/G/A của `y_alpha_1`;
- số enrollment lớp E;
- số họ có ít nhất một enrollment lớp E;
- phân bố `n_c` theo khóa và số khóa dev/test có `n_c >= 30`;
- tỷ lệ có nhãn trên tổng enrollment đủ điều kiện thời gian;
- ICC(1);
- sàn EC trên dev;
- concentration: tỷ trọng khóa lớn nhất, số khóa hiệu dụng và tổng số khóa;
- tỷ lệ user cũ/mới và giảng viên cũ/mới trong test;
- `temporal_overlap`;
- phân bố số khóa trong mỗi family và kết quả sensitivity Jaccard 0,8.

Mọi bảng phải ghi mẫu số. Không dùng tổng bảng audit 11 triệu dòng làm kích thước supervised.

## 8. Validation và sản phẩm nghiệm thu

### 8.1. Validation JSON

`validation.json` cần có tối thiểu:

- row count và unique-key count của từng file;
- null/inf count theo cột;
- duplicate key count;
- class count theo split/phase;
- số enrollment có đủ bốn phase;
- family/course/enrollment leakage checks;
- timestamp cutoff checks;
- train-only preprocessing check;
- feature order/hash;
- target consistency giữa các phase;
- FullTrain-A cohort consistency;
- test-exclusion check cho dev bundle;
- trạng thái từng check và tổng số check đạt.

### 8.2. Cấu trúc thư mục đề nghị

```text
cq_v4/
├── README_HANDOFF.md
├── DATA_CARD_V4.md
├── COURSE_FAMILY_SENSITIVITY.md
├── SHA256SUMS.txt
├── run_manifest.json
├── validation.json
├── splits.json
├── course_family_members.parquet
├── course_family_summary.parquet
├── family_splits.parquet
├── course_splits.parquet
├── feature_dictionary.json
├── selector_feature_columns.json
├── learner_feature_columns.json
├── preprocessing.json
├── pool_b/
│   ├── train.parquet
│   ├── dev_phase1.parquet
│   ├── dev_phase2.parquet
│   ├── dev_phase3.parquet
│   └── dev_phase4.parquet
└── fulltrain_a/
    ├── train.parquet
    ├── feature_columns.json
    ├── preprocessing.json
    ├── validation.json
    └── run_manifest.json
```

Nếu dữ liệu buộc phải partition theo phase/split để giảm kích thước, có thể đổi cấu trúc thư mục nhưng phải giữ cùng contract và cung cấp loader mẫu.

### 8.3. Loader và smoke test

Cung cấp `load_cq_v4.py` hoặc notebook nhỏ thực hiện được:

1. đọc train và bốn dev phase;
2. kiểm tra key/schema;
3. lấy đúng selector/learner feature view;
4. trả về `X`, `y`, `phase`, `course_id`, `course_family_id`, `row_id`;
5. đọc FullTrain-A train;
6. xác nhận dev bundle không chứa test.

Loader không được tự fit lại preprocessing hoặc tự chọn feature theo dtype.

## 9. Tiêu chí chấp nhận bàn giao

Gói chỉ được xem là **READY_FOR_M0_V4** khi đồng thời đạt:

- family mapping hoàn chỉnh và có sensitivity Jaccard 0,8;
- split đúng QĐ19, hash bất biến và không family leakage;
- Pool B train/dev P1–P4 đầy đủ;
- FullTrain-A `lambda=1` có đúng cohort train;
- preprocessing fit train-only và dùng chung;
- selector/learner view tách rõ;
- data card đủ các thống kê bắt buộc;
- validation không có check bắt buộc thất bại;
- dev bundle không chứa feature/label test;
- loader smoke chạy thành công;
- mọi file có SHA-256 và manifest nguồn.

Nếu mục nào chưa đạt, trạng thái phải là `PARTIAL` kèm lý do và thời điểm dự kiến hoàn tất; không gắn `_SUCCESS` chung cho gói chưa đủ contract.

## 10. Thứ tự và thời hạn đề nghị

| Ưu tiên | Việc | Sản phẩm gửi trước | Thời hạn đề nghị |
|---|---|---|---|
| P0.1 | Tạo family mapping và sensitivity | `course_family_members`, summary, báo cáo 0,8/0,9 | Gửi sớm nhất trong ngày 22/10 |
| P0.2 | Khóa split QĐ19 | `splits.json`, family/course split, hash và thống kê leakage | Ngay sau P0.1 |
| P0.3 | Dựng runtime bundle dev-only | Pool B train + dev P1–P4, preprocessing, loader | Chậm nhất 23/10 nếu hạ tầng cho phép |
| P0.4 | Dựng FullTrain-A | Snapshot train `lambda=1`, validation cohort | Cùng hoặc ngay sau runtime bundle |
| P1 | Hoàn thiện data card/validation | Data card V4, manifest, SHA256, báo cáo đầy đủ | Chậm nhất 24/10 |

Nếu P0.3 chưa xong, đề nghị gửi P0.1–P0.2 trước để nhóm thực nghiệm tích hợp schema, viết test và chuẩn bị config, không chờ toàn bộ gói.

## 11. Những việc không được làm

- Không tiếp tục dùng split `course_random` của V3 làm V4.
- Không chia theo user-course.
- Không để các lần mở lại cùng family đi qua nhiều split.
- Không đổi split sau khi xem kết quả mô hình.
- Không dùng test để fit preprocessing, chọn `rho`, chọn candidate hoặc tune learner.
- Không đưa test feature/label vào bundle Kaggle M0-V4.
- Không gọi P4 là FullTrain-A.
- Không tự chuyển target chính sang `y_alpha_0p1`.
- Không fit preprocessor riêng cho từng phase.
- Không xóa lớp E hoặc oversample/balance target trong quá trình tạo dữ liệu chính.
- Không thay công thức nhãn/feature mà không tăng version và ghi deviation.

## 12. Tin nhắn có thể gửi ngay cho nhóm dữ liệu

> Bên thực nghiệm vừa nhận Review-2026-10-22. V4 hiện là đường găng vì toàn bộ kết quả V1/V3 chỉ còn được xem là lịch sử phát triển. Nhờ bên data ưu tiên giúp CQ V4 theo QĐ19: tạo `course_family_id` từ connected components của Jaccard ccid >= 0,9 (mỗi khóa tối thiểu 5 ccid), báo sensitivity 0,8; lấy 20% family mở muộn nhất làm test; 80% còn lại chia train/dev 70:10 bằng seed 42, stratify theo quartile số enrollment có nhãn x `has_E`.
>
> Nhờ gửi P0 trước ngay khi xong gồm mapping family, family/course split, `splits.json`, hash và thống kê leakage. Sau đó cần runtime bundle dev-only: Pool B train + dev P1–P4, preprocessing fit chỉ trên train V4, hai feature view selector/learner, metadata `course_id/course_family_id/row_id`, không chứa test. Đồng thời cần FullTrain-A train ở `lambda=1` trên đúng cohort train V4; P4=0,9 không thay cho FullTrain-A.
>
> Gói hoàn chỉnh cần data card V4, validation, manifest, SHA-256, loader mẫu và các thống kê family/class/concentration/temporal overlap/EC/ICC. Nếu chưa thể gửi cả gói, vui lòng gửi family mapping và split trước để bên mình tích hợp code ngay. Điểm kiểm tra là 29/10 và hiện cần dành thời gian cho chạy thực nghiệm lẫn viết báo cáo, nên nhờ bên data phản hồi ETA cho từng P0.1–P0.4 giúp mình.
