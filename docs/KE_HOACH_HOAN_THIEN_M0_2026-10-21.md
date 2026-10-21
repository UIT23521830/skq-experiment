# Kế hoạch hoàn thiện hồ sơ M0 ngày 21 tháng 10 năm 2026

## 1. Mục tiêu và nguyên tắc

Mục tiêu của kế hoạch này là hoàn thiện toàn bộ sản phẩm M0 được giao trong hai
bản review ngày 12 và 13 tháng 10 năm 2026, đồng thời phân biệt rõ bằng chứng đã
đạt, bằng chứng tạm thời và hạng mục bị chặn bởi dữ liệu nguồn.

Các nguyên tắc không được vi phạm:

1. M0 chỉ dùng train và dev để chọn giao thức, ngân sách và chính sách trọng số.
2. Không fit, dự đoán, tính metric hoặc chọn cấu hình bằng test trước freeze M1.
3. Không đổi một hạng mục bị thiếu thành PASS bằng suy đoán. Phải ghi BLOCKED,
   nguyên nhân, bằng chứng đã kiểm tra và dữ liệu cần bổ sung.
4. Tách commit chạy thực nghiệm, config, split hash, run ID và artifact hash.
5. Kết quả cũ ở commit trước dual-view chỉ là bằng chứng chẩn đoán, không dùng để
   chọn phương pháp hoặc khóa giao thức.

## 2. Thuật ngữ phải thống nhất

### 2.1. Pool B

Pool B là tập huấn luyện dùng chung cho bảng coreset chính. Với mỗi lượt ghi danh
`(learner, course)` thuộc các khóa train, Pool B chứa bốn snapshot P1, P2, P3 và
P4 cùng nhãn cấp lượt ghi danh và chỉ báo giai đoạn. Vì vậy một lượt ghi danh có
tối đa bốn dòng trong Pool B.

Pool B không phải một split mới, không chứa dev hoặc test, và không phải một
phương pháp. Đây là pool đầu vào mà mọi selector cùng nhận để bảo đảm so sánh
công bằng.

### 2.2. FullTrain-A và FullTrain-B

- FullTrain-A dùng cấu hình huấn luyện nguyên của TEMPO-DQ trên cùng các khóa
  train, trong đó train giữ hành vi đầy đủ của lượt ghi danh. Nó là tham chiếu
  với quy trình nguồn.
- FullTrain-B huấn luyện trên toàn bộ Pool B, tức toàn bộ snapshot P1-P4 của các
  lượt ghi danh thuộc khóa train, không chọn coreset. Nó là tham chiếu trực tiếp
  cho các selector chạy trên Pool B.
- P4 dùng mốc 90 phần trăm tiến độ nên không được tự xem là FullTrain-A. Chỉ được
  làm vậy nếu người tạo dữ liệu hoặc giảng viên xác nhận bằng văn bản.

### 2.3. Kiểm tra bắt buộc và ablation

Review gọi là “kiểm tra 1-12”, không đặt mã D. Repo hiện dùng D01-D12 cho các
diagnostic, trong khi review cũng nhắc các biến thể cũ D02, D04 và D05. Để tránh
nhầm, báo cáo M0 dùng mã `CHK01` đến `CHK12`. Tên field D01-D12 hiện có trong
artifact chỉ được giữ như alias kỹ thuật.

Ablation dùng mã `A1` đến `A8` và là một nhóm hoàn toàn khác. Ablation trả lời
thành phần nào của SKQ-PC có tác dụng; các kiểm tra CHK bảo vệ tính hợp lệ của dữ
liệu và pipeline.

## 3. Ánh xạ 12 kiểm tra bắt buộc

| Mã báo cáo | Nội dung review | Mục đích | Bằng chứng cần có | Mốc |
|---|---|---|---|---|
| CHK01 | Kích thước và phân bố | Kiểm tra số khóa, lượt ghi danh, dòng, lớp theo split và phase; không trùng group | Bảng phân bố, overlap assertion, tỷ lệ khóa chưa kết thúc và đối tượng cũ/mới | M0 |
| CHK02 | Probe chỉ dùng mã định danh | Phát hiện leakage hoặc split sai | Macro-F1 của course ID, teacher ID, school ID và majority | M0 |
| CHK03 | Dữ liệu thiếu | Tái lập missingness probe TEMPO-DQ, không đưa missing mask vào feature | AUC probe và danh sách cột | M0; BLOCKED nếu không có pre-imputation data |
| CHK04 | Nhãn xáo trộn | Phát hiện leakage trong learner pipeline | XGBoost FullTrain-B trên dev phải về mức ngẫu nhiên | M0 |
| CHK05 | Mức sàn | Có baseline tối thiểu để diễn giải kết quả | Majority theo phase; chỉ số tạm tính nếu có | M0 |
| CHK06 | Mốc cắt | Chứng minh snapshot không dùng sự kiện tương lai | Audit thủ công 20 cặp learner-course với timestamp lớn nhất không vượt cutoff | M0; BLOCKED nếu thiếu raw timestamp |
| CHK07 | Contract trọng số | Chứng minh khối lượng tầng và thứ tự sample weight đúng | Mass error, all-one, zero-weight, scaling tests và run artifact | M0 |
| CHK08 | Tái lập baseline | Không đưa adapter sai vào bảng chính | Toy/benchmark fidelity và source commit cho từng baseline mới | Trước M1, không bắt buộc hoàn tất tại M0 |
| CHK09 | Đơn vị và nhãn | Xác nhận một dòng gốc là một lượt ghi danh | Unique `(course_id, learner_id)`, `y=tau(q)`, nhãn thay đổi trong khóa | M0 |
| CHK10 | Không lọt nhãn vào X | Ngăn target leakage | Assert q, y, coelo, afelo, acelo và cột dẫn xuất không nằm trong feature | M0 |
| CHK11 | Tái tính tổng hợp | Chứng minh Qc/Yc có thể tái lập | Sai khác Qc dưới `1e-9`, phân bố Yc theo split | M0 |
| CHK12 | Hằng số giao thức | Khóa các hằng số chỉ lấy từ train | `mu_E < mu_G < mu_A`, mỗi giá trị nằm đúng dải lớp | M0 |

## 4. Ánh xạ ablation A1-A8

| Mã | Cấu hình | Câu hỏi cơ chế | Phạm vi |
|---|---|---|---|
| A1 | SKQ-PC bản chốt | Phương pháp đầy đủ | Phương pháp chính |
| A2 | Chỉ phân tầng theo lớp, bỏ giai đoạn | Phân tầng giai đoạn có cần không? | Bắt buộc cho bài ICCIES nếu GO |
| A3 | Random trong ô thay herding | Herding có tạo lợi ích không? | Luận văn hoặc nhánh NO-GO |
| A4 | Bỏ QP, dùng trọng số đều trong tầng | QP có cần không? | Bắt buộc cho bài ICCIES nếu GO |
| A5 | Bỏ Voronoi, RFF quadrature trên toàn tầng | Cấu trúc ô cha có cần không? | Luận văn hoặc nhánh NO-GO |
| A6 | Thêm hoặc bỏ LRQ so với bản chốt | Query-aware loss có cần không? | Luận văn hoặc nhánh NO-GO |
| A7 | Độ nhạy D, bandwidth, K và allocation | Kết quả có ổn định với siêu tham số không? | Dev sau khi chốt; không dùng để chọn bằng test |
| A8 | Hiệu chỉnh prior hậu kiểm | Lợi ích EC có chỉ đến từ sửa prior không? | Bắt buộc khi báo cáo EC; không huấn luyện lại |

Tổng cộng có tám nhãn A1-A8, nhưng A1 là phương pháp đầy đủ. Có bảy phép loại
bỏ, thay thế hoặc phân tích. M0 chưa yêu cầu chạy toàn bộ ablation. Nếu GO, phạm
vi bài dùng A1, A2, A4 và A8; A3, A5, A6 và A7 dành cho luận văn hoặc nhánh
NO-GO.

## 5. Cách xác nhận group unit

### 5.1. Hai khái niệm không được trộn

- Enrollment uniqueness: một người học đăng ký một lần trong một lần mở khóa,
  kiểm bằng unique `(learner_id, course_id)`. Đây là CHK09.
- Course group unit: nhiều `course_id` có thể là nhiều lần mở của cùng một khóa
  gốc. Mọi lần mở của cùng khóa gốc phải nằm trong cùng split. Đây là contract
  split và độc lập với enrollment uniqueness.

### 5.2. Trình tự xác nhận

1. Gửi người tạo dữ liệu câu hỏi chính xác: “`course_id` là một khóa gốc hay một
   lần mở? Có khóa gốc nào được mở nhiều lần không? Nếu có, vui lòng cung cấp
   mapping `course_id -> course_root_id`; nếu không, vui lòng xác nhận mỗi
   `course_id` tương ứng duy nhất một khóa gốc trong CQ v1.”
2. Nếu có mapping, kiểm tra mỗi `course_id` ánh xạ đúng một `course_root_id`,
   thống kê số root có nhiều lần mở và ngày mở đầu tiên của root.
3. Nếu không có khóa mở lại và có xác nhận bằng văn bản, tạo
   `course_root_id = course_id`, lưu nội dung xác nhận, người xác nhận và ngày.
4. Chia temporal theo `course_root_id`, dùng ngày mở đầu tiên của root. Nếu ngày
   không đáng tin cậy hoặc test thiếu lớp, chuyển sang StratifiedGroupKFold theo
   quyết định tại M0, không tự đổi sau M0.
5. Assert giao của root giữa train/dev/test bằng rỗng.
6. Xuất `splits.json`, bản mapping private và SHA-256. Bản công khai chỉ chứa
   hash và thống kê, không chứa ID nhạy cảm.
7. Chỉ sau bước này mới chuyển endpoint theo khóa từ `provisional_course_id`
   sang đủ điều kiện confirmatory.

## 6. Kế hoạch thực hiện tuần tự

### Giai đoạn 0 — Khóa phạm vi và nguồn sự thật

#### Bước 0.1. Khóa trạng thái hiện tại

- Nhánh làm việc: `cq-v1-protocol-fixes`.
- Commit thực nghiệm của cell M0: `6c1b336a8c43e9c5e6a757df48db4d3d538d29bd`.
- Không dùng lại số liệu screening tại commit `46f733a` để chọn phương pháp.
- Giữ `test_locked=true` trong mọi config M0.

Sản phẩm: một dòng provenance trong báo cáo gồm branch, experiment commit, cell
commit, dataset version và thời điểm chạy.

#### Bước 0.2. Chạy cell M0 dev-only hiện tại

- Chạy đến khi tạo archive thành công.
- Không giảm replicate của QĐ16.
- Tải archive, notebook log và trạng thái Kaggle.

Điều kiện đạt: archive mở được; có commit file, configs, artifacts, M0 docs và
log; không có test metric.

#### Bước 0.3. Kiểm kê archive

- Lập inventory file và SHA-256.
- Kiểm tra run thành công/thất bại/blocked, không bỏ run lỗi.
- Đối chiếu config hash, split hash, feature contract và commit.
- Cập nhật báo cáo từ commit cũ sang commit mới.

Sản phẩm: `M0_ARCHIVE_INVENTORY.csv`, `SHA256SUMS.txt`, bảng run completeness.

### Giai đoạn 1 — Chốt contract dữ liệu

#### Bước 1.1. Chốt group unit

Thực hiện toàn bộ trình tự ở Mục 5. Nếu chưa nhận được xác nhận, giữ trạng thái
`BLOCKED_GROUP_UNIT_CONFIRMATION`; không mở test và không tạo freeze M1.

#### Bước 1.2. Hoàn thiện lược đồ cột

Với từng cột, ghi:

- tên và kiểu dữ liệu;
- cấp đơn vị: event, chapter, enrollment, course;
- nguồn và phép tính;
- thời điểm cột khả dụng;
- phép gộp chapter lên enrollment;
- static hay behavior;
- có dùng cho selector không;
- có dùng cho learner không;
- lý do loại;
- target-derived/leakage flag;
- xử lý thiếu và fit preprocessing trên split nào.

Sản phẩm: `COLUMN_SCHEMA_M0.xlsx` và bản CSV.

#### Bước 1.3. Hoàn thiện data card

Bổ sung:

- nguồn và phiên bản CQ v1;
- đơn vị dòng và group unit;
- công thức q, y, Qc, Yc và quy ước biên 0,2/0,4;
- ý nghĩa `euclid_to_111`, AFELO/COELO/ACELO;
- chuẩn hóa min-max và tập tham chiếu;
- cách tính chương chưa mở;
- P1-P4 và cutoff;
- xử lý thiếu;
- feature view selector và learner;
- phân bố split, lớp, `n_c`, ICC(1), `mu_y`, oracle floor;
- privacy, hash và giới hạn sử dụng.

Các thông tin chưa xác nhận phải có nhãn `PENDING_DATA_OWNER`, không tự điền.

#### Bước 1.4. Sinh split manifest

- Xuất private mapping group-to-split.
- Xuất `splits.json`, `split_manifest.json` và SHA-256.
- Kiểm tra disjoint group và temporal overlap.
- Ghi chiến lược chính hoặc fallback và lý do quyết định tại M0.

### Giai đoạn 2 — Đóng 12 kiểm tra bắt buộc

#### Bước 2.1. Chạy các kiểm tra có đủ dữ liệu

Chạy CHK01, CHK02, CHK04, CHK05, CHK07, CHK09, CHK10, CHK11 và CHK12 trên
commit mới. Mỗi kiểm tra lưu input hash, command, output, trạng thái và fail
action.

#### Bước 2.2. Xử lý CHK03 và CHK06

- Xin pre-imputation matrix cho CHK03.
- Xin raw event timestamp hoặc audit có chữ ký/xác nhận của người tạo dữ liệu
  cho CHK06.
- Nếu không có trước M0, ghi BLOCKED; không ghi PASS bằng model-ready parquet.

#### Bước 2.3. Theo dõi CHK08

- G10 hiện chỉ là fidelity toy của baseline.
- Lập bảng từng baseline: nguồn chính thức, commit, adaptation, toy/benchmark,
  trạng thái PASS/FAIL/BLOCKED.
- Hoàn tất trước freeze M1, không dùng CHK08 để giả thiếu tại M0.

Sản phẩm: `CHECKS_01_12_M0.xlsx`, JSON máy đọc và thư mục evidence.

### Giai đoạn 3 — Hoàn thiện FullTrain và hai endpoint

#### Bước 3.1. Xác nhận nguồn FullTrain-A

- Yêu cầu full-behavior train table theo TEMPO-DQ trên đúng các khóa train.
- Nếu không tồn tại, hỏi giảng viên có chấp nhận FullTrain-A là unavailable hoặc
  định nghĩa thay thế nào.
- Không tự dùng P4 vì P4 chỉ đến 90 phần trăm tiến độ.

#### Bước 3.2. Khóa learner tuning

- Tune một lần trên FullTrain-B/train với dev, tối đa tám cấu hình mỗi learner.
- XGBoost và LR dùng cùng cấu hình thắng cho mọi selector.
- Không tune lại theo phương pháp; không dùng test.
- Lưu grid, metric chọn, best config và early-stopping iteration.

#### Bước 3.3. Chạy FullTrain-B

Chạy bốn tổ hợp:

1. XGBoost + natural weights;
2. XGBoost + balanced weights;
3. LR + natural weights;
4. LR + balanced weights.

Lưu probability cho P1-P4, per-label metrics, confusion matrix, fit time và
environment.

#### Bước 3.4. Chạy FullTrain-A

Sau khi có full-behavior table, chạy XGBoost và LR theo cùng protocol. Nếu review
yêu cầu so chính sách trọng số cho A, ghi rõ trong config; không tự mở rộng nếu
không cần.

#### Bước 3.5. Tính UL và EC

- UL: Macro-F1 trung bình P1-P4 ở cấp lượt ghi danh.
- EC: MAE của Q-hat theo PCC, trung bình P1-P4 trên khóa đủ `n_min`.
- Báo thêm từng phase, MCC, balanced accuracy, log loss, ECE, per-label metrics,
  CC sensitivity và A8 khi phù hợp.
- Bootstrap theo group unit đã chốt; phase không phải replicate độc lập.

#### Bước 3.6. Chuẩn bị quyết định M0

- So natural với balanced trên UL và EC.
- Trình giảng viên chọn class-weight policy.
- Trình `n_min`, oracle floor và `delta_C`; không tự sửa sau M0.
- Tính nửa độ rộng CI dev để quyết định temporal split hay SGKF.

### Giai đoạn 4 — Chạy lại headroom QĐ12

#### Bước 4.1. Chạy đúng input

- Chỉ dùng FullTrain-B và C02.
- C02 chạy tại 0,5%, 1%, 2% và 5%.
- Mỗi mức dùng selector seed 11, 29 và 47.
- Dùng dual-view, learner config và weight policy mới.

#### Bước 4.2. Chọn ngân sách

Tính `delta(rho) = UL(FullTrain-B) - mean_seed UL(C02, rho)`. Chọn rho lớn nhất
có delta không nhỏ hơn 0,01; nếu không có mức đạt, chọn 0,5 phần trăm.

#### Bước 4.3. Khóa evidence

Xuất bảng mean, SD, từng seed, delta, quyết định rho, commit, config hash và xác
nhận test chưa mở. Kết quả rho bằng 2 phần trăm ở commit cũ không được tự động
chuyển sang giao thức mới.

### Giai đoạn 5 — Hoàn thiện tài nguyên QĐ16

#### Bước 5.1. Kiểm kê máy

Lưu CPU, số core/thread, RAM, GPU, số GPU, VRAM, driver, CUDA, Python, phiên bản
thư viện, dung lượng đĩa, giới hạn phiên và giờ khả dụng mỗi tuần.

#### Bước 5.2. Hiệu chuẩn từng selector

- Mẫu phân tầng phase x class ở 50k, 200k và 800k dòng.
- Ba lần đo steady-state mỗi cỡ; warm-up ghi riêng.
- Dùng rho đã chốt.
- Ghi thiết bị thực tế CPU/GPU, wall-clock và peak RSS.
- Mở rộng script hiện tại từ ba SKQ candidate sang mọi selector thuộc phạm vi M0.

#### Bước 5.3. Ra quyết định resource gate

- Fit hồi quy log-log và dự báo tới toàn Pool B.
- Không quá 3 giờ: `RUN`.
- Quá 3 giờ: chạy lại với shard wrapper chung.
- Vẫn quá: `TIMEOUT`, giữ trong mẫu số và ghi thời gian dự báo.
- GPU-giờ cấp phát = wall-clock nhân số GPU được cấp; không quy đổi theo utilization.

#### Bước 5.4. Ước lượng phạm vi ICCIES

Từ bảng đo, dự báo tổng thời gian dev và test. Điều kiện GO là hoàn tất tối đa
bốn ngày dev và ba ngày test với tài nguyên đã khai báo.

### Giai đoạn 6 — Pytest và tái lập

#### Bước 6.1. Chạy test bắt buộc

Chạy ít nhất:

- `tests/test_cq_protocol.py`;
- contract tương đương `cq_patch_1013`;
- `tests/test_cq_m0_audit.py`;
- `tests/test_feature_views.py`;
- `tests/test_weights.py`;
- `tests/test_headroom.py`;
- `tests/test_resource_calibration.py`;
- freeze tests liên quan M0/M1.

Nếu file `test_cq_patch_1013_contracts.py` chưa tồn tại, tạo file ánh xạ các contract
QĐ12-QĐ16 thay vì chỉ nói chức năng đã nằm rải rác ở test khác.

#### Bước 6.2. Lưu evidence tái lập

- Lưu command, stdout/stderr, JUnit XML, số pass/fail/skip và commit.
- Viết README một lệnh cho lượt M0 dev-only.
- Không xóa hoặc gộp lỗi.

### Giai đoạn 7 — Hoàn thiện tài liệu M0

#### Bước 7.1. Báo cáo phản hồi M0

Cập nhật báo cáo theo evidence mới, gồm:

- requirement-to-evidence matrix;
- data/split/check status;
- FullTrain-A/B và UL/EC;
- headroom và rho;
- resource gate;
- pytest;
- PASS/PARTIAL/BLOCKED;
- câu hỏi cần giảng viên quyết định;
- không dùng kết quả screening cũ làm kết luận.

#### Bước 7.2. Đề cương v2

Dùng đề cương Overleaf cũ làm nền và sửa:

- bài toán hai cấp;
- RQ1-RQ5 và H1-H4;
- CQ v1, Pool B, FullTrain-A/B;
- SKQ-PC tối đa ba candidate dev;
- baseline chốt và CoreTab-OVA adapted;
- UL/EC, K1-K5, K1c-K5c;
- headroom, weights, resource gate;
- split/freeze/test policy;
- timeline, rủi ro, Plan B và sản phẩm;
- privacy và tái lập.

Đầu ra: nguồn TeX và PDF `DE_CUONG_V2_M0`.

#### Bước 7.3. Khung bài LNCS

Không chỉ để tiêu đề và TODO. Tại M0 phải có nội dung do nhóm tác giả viết ở:

- Introduction;
- Related Work;
- Problem Formulation;
- Data and Protocol;
- Method outline.

Chưa viết claim test, kết luận vượt trội hoặc số liệu confirmatory. Nhóm tự viết
văn bản theo quy định hội nghị; công cụ chỉ chuẩn bị outline, công thức, bảng và
evidence để tác giả diễn đạt lại.

Đầu ra: `main.tex`, `references.bib`, PDF compile thành công.

#### Bước 7.4. Tính mới và tài liệu tham khảo

- Chạy các truy vấn đã đăng ký trên Scholar, Scopus, arXiv, Semantic Scholar và
  venue liên quan.
- Ghi query, ngày, số kết quả, bài liên quan, lý do giữ/loại và kết luận.
- Sửa metadata BibTeX được review chỉ ra.
- Không dùng “novel”, “first” hoặc “SOTA” khi ledger chưa đủ.

#### Bước 7.5. Privacy và quyền truy cập

Phần này tách khỏi kết quả mô hình nhưng vẫn là sản phẩm M0:

- xác nhận dataset/notebook Private;
- quyền repo/Drive;
- tag và commit;
- download count nếu nền tảng hiển thị;
- quyết định xử lý workbook trong Git history.

### Giai đoạn 8 — Đóng gói và ra quyết định

#### Bước 8.1. Cấu trúc gói nộp

```text
M0_PACKET_2026-10-21/
  00_README_M0.md
  01_BAO_CAO_PHAN_HOI_M0.docx
  02_REQUIREMENT_EVIDENCE_MATRIX.xlsx
  data/
  checks/
  experiments/
  resources/
  documents/
  blockers/
  SHA256SUMS.txt
```

#### Bước 8.2. Kiểm tra bốn tiêu chí GO

1. Data card, split và CHK01-CHK07, CHK09-CHK12 đủ hoặc blocker được giảng viên
   chấp thuận.
2. FullTrain-A/B đã chạy trên dev với XGBoost và LR, đủ UL/EC.
3. Timing QĐ16 chứng minh phạm vi hoàn tất trong bốn ngày dev và ba ngày test.
4. Khung bài có nội dung Introduction, Related Work, Problem và Data.

#### Bước 8.3. Phân loại kết quả

- `GO`: đủ bốn điều kiện và không còn blocker giao thức bắt buộc.
- `GO_CONDITIONAL`: code, dev evidence, timing và tài liệu đủ nhưng còn xác nhận
  dữ liệu mà giảng viên chấp thuận cho đóng sau.
- `NO_GO_M0`: thiếu FullTrain-A/B, split/group không hợp lệ, dùng test để bù bằng
  chứng, hoặc timing không khả thi.

## 7. Các luồng có thể làm song song

### Luồng A — Chờ người tạo dữ liệu

- group-unit confirmation;
- mapping course root nếu có;
- pre-imputation data;
- raw timestamp;
- FullTrain-A/full-behavior table;
- mô tả chính thức cách tính nhãn.

### Luồng B — Kaggle

- cell M0 dev-only;
- FullTrain-B;
- headroom rerun;
- resource calibration;
- pytest và archive.

### Luồng C — Tài liệu

- column schema;
- data card phần đã biết;
- đề cương v2;
- LNCS sections;
- novelty ledger và BibTeX;
- báo cáo M0 và evidence matrix.

### Luồng D — Repo và privacy

- quyền truy cập;
- tag/commit;
- Git-history privacy decision;
- README một lệnh.

Luồng C không cần chờ toàn bộ thực nghiệm; để placeholder có ID bằng chứng và chỉ
điền số sau khi archive được kiểm tra. Luồng B không được chờ phần văn bản. Luồng
A có thể tạo blocker nhưng không được dùng làm lý do dừng các phần còn lại.

## 8. Thứ tự ưu tiên ngay lập tức

1. Chạy xong cell M0 hiện tại và bảo toàn archive/log.
2. Gửi câu hỏi group unit, raw timestamp, pre-imputation và FullTrain-A cho người
   tạo dữ liệu ngay trong một tin nhắn.
3. Kiểm kê archive và cập nhật status CHK.
4. Chạy lại headroom trên dual-view.
5. Mở rộng resource calibration cho panel còn thiếu.
6. Song song cập nhật đề cương v2 và viết nội dung thật cho khung LNCS.
7. Đóng gói M0 packet với PASS/PARTIAL/BLOCKED trung thực.
8. Chỉ tạo freeze M1 và mở test sau khi M0 được chấp thuận.
