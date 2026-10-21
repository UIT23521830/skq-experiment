# Audit evidence M0 CQ v1 ngày 21/10/2026

## 1. Phạm vi và provenance

- Archive nguồn: `results/cq_v1/skq_cq_v1_m0_evidence_2026_10_21.tar.gz`.
- SHA-256: `6EB2757679831986852AD60C1DA0D822971B69A13FD81459C0396D806FBB2939`.
- Kích thước: 18.654.497 byte.
- Commit đã chạy trên Kaggle: `6c1b336a8c43e9c5e6a757df48db4d3d538d29bd`.
- Thời gian UTC: 02:52:31--06:33:29 ngày 21/10/2026.
- Thiết bị được cấp: 2 Tesla T4 15 GiB; selector trong lượt này chủ yếu CPU-bound.
- Phạm vi: development-only; không đọc metric test.
- Group unit: `course_id` tạm thời; chưa đủ điều kiện confirmatory.

Archive ghi `success` cho toàn bộ bước 00--10. Điều này xác nhận pipeline đã chạy
hết, không xác nhận rằng toàn bộ tiêu chí GO M0 đã đạt.

## 2. Phát hiện lỗi endpoint và cách sửa

Artifact endpoint trong archive gốc ghi `UL=0` vì `y_true/y_pred` được lưu dưới
dạng số `0/1/2`, còn hàm Macro-F1 yêu cầu nhãn `E/G/A`. Đây là lỗi tổng hợp
evidence, không phải mô hình dự đoán toàn sai. `run_ledger.json` vẫn chứa metric
khác 0.

Bản sửa:

1. Chuẩn hóa cả nhãn số và nhãn chuỗi trước khi tính UL.
2. Prediction artifact mới lưu nhãn `E/G/A`, nhưng vẫn kiểm tra mã số trong NPZ.
3. Lưu `effective_class_prior` thật sự learner nhìn thấy sau khi ghép và chuẩn hóa
   sample weight.
4. Cài A8 prior correction theo label-shift, tách metric gốc và metric hiệu chỉnh,
   không fit lại learner.
5. Thêm test hồi quy để lỗi kiểu nhãn không tái diễn.

Các số bên dưới được tính lại từ prediction có sẵn trong archive; không huấn
luyện lại và không mở test. Archive gốc vẫn bất biến theo SHA-256 ở trên.

## 3. FullTrain-B dev sau khi sửa UL

### 3.1. Trung bình P1--P4

| Class policy | Learner | UL gốc | EC gốc | UL sau A8 | EC sau A8 | Delta UL | EC giảm |
|---|---:|---:|---:|---:|---:|---:|---:|
| balanced | LR | 0.449419 | 0.219868 | 0.606372 | 0.089434 | +0.156953 | +0.130434 |
| balanced | XGB | 0.599168 | 0.134398 | 0.544311 | 0.082297 | -0.054857 | +0.052101 |
| natural | LR | 0.526336 | 0.161484 | 0.526336 | 0.161484 | 0.000000 | 0.000000 |
| natural | XGB | **0.654338** | **0.080661** | 0.654338 | 0.080661 | 0.000000 | 0.000000 |

`EC giảm` là `EC_gốc - EC_A8`, vì EC thấp hơn là tốt hơn. Natural là phép đồng
nhất của A8 do prior nguồn bằng prior Pool B. Prior natural là
`E=0.031852, G=0.176057, A=0.792091`; prior balanced là `1/3` cho mỗi lớp.

Kết luận dev tạm thời:

- FullTrain-B natural XGB đang tốt nhất đồng thời ở UL và EC trước A8.
- A8 giúp balanced XGB giảm EC mạnh nhưng đánh đổi UL; vì vậy không được chỉ báo
  EC hoặc chỉ báo UL.
- A8 giúp balanced LR cả UL lẫn EC, nhưng mọi kết quả LR hiện chỉ descriptive do
  chưa hội tụ.
- Oracle floor EC trên 61 khóa đủ `n_min=30` là 0.058789. Natural XGB còn cách
  floor khoảng 0.021872.

### 3.2. Theo phase

| Policy/Learner | P1 UL/EC | P2 UL/EC | P3 UL/EC | P4 UL/EC |
|---|---:|---:|---:|---:|
| balanced LR | 0.440729 / 0.213682 | 0.450997 / 0.220186 | 0.453096 / 0.222708 | 0.452855 / 0.222897 |
| balanced XGB | 0.546579 / 0.148897 | 0.595107 / 0.134070 | 0.622851 / 0.128826 | 0.632133 / 0.125799 |
| natural LR | 0.500533 / 0.160159 | 0.524954 / 0.160836 | 0.538136 / 0.162093 | 0.541719 / 0.162851 |
| natural XGB | 0.634999 / 0.082594 | 0.667099 / 0.079409 | 0.665149 / 0.080333 | 0.650105 / 0.080308 |

Mỗi EC phase chỉ dùng 61/266 khóa dev vì 205 khóa dưới `n_min=30`. Phải báo cả
mẫu số này, không được trình bày EC như đại diện cho toàn bộ 266 khóa.

## 4. Data card và kiểm tra 1--12

Đã đạt trên evidence hiện có:

- D01 phân bố/size theo split.
- D02 ID-only probe: course ID bằng majority; dev course đều unseen.
- D04 shuffled-label XGB bằng majority, Macro-F1 0.251565 ở P1--P4.
- D05 majority baseline.
- D07 code contract weight; test thực thi được bổ sung trong suite M0.
- D09 đơn vị dòng enrollment.
- D10 không có target trong selector view.
- D11 tái tính Qc/Yc từ enrollment q.
- D12 hằng số protocol.

Chưa thể hoàn tất từ snapshot model-ready:

- D03 missingness trước imputation: cần raw pre-imputation matrix.
- D06 kiểm tra thủ công 20 cutoff: cần raw event timestamps.
- `course_root_id`: đang chờ xác nhận rằng mỗi `course_id` chỉ mở một lần hoặc
  mapping root thật. Vì vậy split hiện chỉ provisional.
- D08 baseline fidelity được review cho phép dời tới M1.

## 5. LR convergence

Cả 8 fit LR (balanced/natural x P1--P4) đều chạm `max_iter=5000` và phát
`ConvergenceWarning`. Không được dùng các số LR để tuyên bố thắng/thua. Bước đúng
tiếp theo là tuning tối đa 8 cấu hình trên dev theo O16, lưu cấu hình thắng rồi
freeze; không tăng `max_iter` tùy tiện và không dùng test.

## 6. Hiệu chuẩn tài nguyên QĐ16

Mỗi candidate đã đo tại 50k/200k/800k, ba replicate, warm-up riêng, rho=2%.

| Candidate | Dự báo toàn Pool B | Upper diagnostic | Peak RSS dự báo | Peak RSS upper | Quyết định |
|---|---:|---:|---:|---:|---|
| SKQ-PC | 188.14 s | 490.49 s | 5.26 GiB | 7.93 GiB | run direct |
| SKQ-PC + LRQ-SQ | 2454.85 s | 4391.11 s | 11.85 GiB | 16.40 GiB | run direct |
| SKQ-PC-R | 52.92 s | 74.95 s | 5.23 GiB | 8.06 GiB | run direct |

Lượt notebook lâu chủ yếu do LRQ-SQ: riêng ba replicate 800k mất khoảng 31 phút
mỗi replicate. Đây là compute thật, không phải lỗi lưu archive. Cả ba candidate
đều dưới trần selector 3 giờ. Tuy nhiên QĐ16 yêu cầu 10 selector cố định cộng ba
candidate; archive này mới hoàn tất ba candidate nên resource gate M0 vẫn PARTIAL.

Mã calibration mới ghi tiến trình từng warm-up/replicate và checkpoint sau mỗi
observation. `--resume` chỉ nhận checkpoint cùng method và environment, giúp mất
mạng không phải chạy lại các điểm đã hoàn tất.

## 7. Pytest và tái lập

- Bộ contract M0 chọn lọc: 51/51 pass cục bộ.
- Toàn repo: 166/166 pass cục bộ.
- Đã thêm `tests/test_cq_patch_1013_contracts.py` với đúng bảy test được Review 13
  gọi tên.
- Cell Kaggle mới chạy bộ M0 và lưu `m0_docs/cq_v1/pytest_m0_contracts.xml` vào
  archive. Archive hiện tại chưa có JUnit XML vì được tạo trước bản sửa này.

## 8. Trạng thái GO M0 ngày 21/10

**Kết luận: PARTIAL, chưa được ghi GO.**

Đã có: Pool B provisional, data card dev-only, FullTrain-B natural/balanced,
UL/EC đã sửa, A8, ba candidate timing và code/test nền.

Còn thiếu trước khi trình GO:

1. FullTrain-A trên cùng dev và feature contract.
2. Headroom đầy đủ C02: bốn rho `0.5/1/2/5%` x seed `11/29/47`, sau đó chốt
   `rho*` chỉ từ FullTrain-B và C02.
3. Timing của 10 selector cố định ở `rho*`; ba candidate đã xong.
4. LR hội tụ theo tuning dev-only hoặc ghi loại LR khỏi evidence quyết định theo
   protocol đã được duyệt.
5. JUnit Kaggle của hai nhóm contract `cq_protocol` và `cq_patch_1013`.
6. Xác nhận Private; D03/D06 raw evidence; quyết định `course_root_id`.
7. Bảng ước lượng tổng thời gian dev <=4 ngày và test <=3 ngày sau khi đủ 13
   selector.

Không cần chạy lại toàn bộ archive chỉ để sửa UL. Có thể tái tính endpoint từ
prediction hiện có. Lượt Kaggle tiếp theo nên dành cho FullTrain-A, headroom còn
thiếu, LR convergence và timing 10 selector; tuyệt đối chưa mở test metric.

Code đã chuẩn bị một cell headroom độc lập, bốn config C02 và script quyết định
strict để chạy đúng 1 FullTrain-B XGB + 4 rho x 3 seed. Policy trong cell được
ghi là `natural_provisional_pending_supervisor_confirmation`: kết quả có thể dùng
làm evidence dev, nhưng không tự động biến thành policy freeze trước khi giảng
viên xác nhận.
