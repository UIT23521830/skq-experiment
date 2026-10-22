# Báo cáo phản hồi Review ngày 12 và 13 tháng 10 năm 2026

**Ngày cập nhật:** 21/10/2026

**Nhánh thực hiện:** `cq-v1-protocol-fixes`

**Commit dùng cho headroom M0 hiện tại:** `9b07f6f769d8504a2555bf6608411c8f5131f8be`

**Commit screening lịch sử:** `46f733a55f754b699656a0e69c1e24911d79891d`
**Phạm vi báo cáo:** Những hạng mục đã có bằng chứng đến hết FullTrain-B, audit M0 và headroom QĐ12 trên dev. Các hạng mục chưa đủ bằng chứng được ghi rõ là chưa hoàn tất; báo cáo không sử dụng kết quả test CQ v1.

## 1. Kết luận và đề nghị hiện tại

Nhóm đã chuyển được trọng tâm thực nghiệm từ Adult/CQ_med sang CQ v1 ở cấp lượt ghi danh và đã chạy vòng development đầu tiên theo bốn giai đoạn P1--P4. Test CQ v1 vẫn khóa. Lượt headroom M0 mới, đúng dual-view và chỉ dùng FullTrain-B cùng C02 trên dev, đã hoàn tất 52/52 lượt đánh giá và 54/54 kiểm thử contract. Không mức ngân sách nào thỏa ngưỡng chênh lệch đăng ký `0,01`; quy tắc fallback vì vậy chọn ngân sách nhỏ nhất `rho*=0,5%`. Kết quả này thay thế quyết định headroom `2%` trước đây. Vòng screening sáu cấu hình tại `2%` vẫn được giữ làm evidence chẩn đoán lịch sử, không dùng để chốt M1.

Kết quả hiện tại chưa đủ để chọn phương pháp cuối cùng hoặc mở test. `SKQ-PC-LRQ-SQ` là ứng viên SKQ tốt nhất về Macro-F1, MCC và log loss, nhưng không cải thiện recall của lớp hiếm và tốn thời gian chọn mẫu cao hơn C03 rất nhiều. Sau audit M0, nhóm còn phát hiện screening ở commit `46f733a` đã dùng 56 feature hành vi cho cả selector và learner, trong khi O17/QĐ3 yêu cầu learner giữ các mã tĩnh của TEMPO-DQ. Vì vậy vòng screening này chỉ còn là evidence chẩn đoán lịch sử và phải chạy lại sau sửa dual-view; chưa được dùng để chọn winner M1.

Hai blocker chính của confirmatory là:

1. Snapshot chưa có `course_root_id`, nên chưa thể chứng minh disjoint theo khóa gốc hoặc chạy cluster bootstrap đúng đơn vị khi một khóa có nhiều lần mở.
2. FullTrain-B đã có XGBoost và LR, natural/balanced cùng UL/EC provisional; tuy nhiên toàn bộ LR chưa hội tụ, FullTrain-A chưa có đúng nguồn, EC vẫn chờ chốt group unit. QĐ16 tại `rho*=0,5%` và freeze M1 chưa hoàn tất.

## 2. Phạm vi dữ liệu và giao thức đã chạy

CQ v1 hiện tại có Pool B gồm 994.608 snapshot, được ghép từ bốn phase train; mỗi phase có 248.652 lượt ghi danh. Mỗi phase dev có 31.028 dòng. Mỗi phase test có 28.318 dòng nhưng chưa được đọc để đánh giá mô hình. Ở vòng screening lịch sử, 56 feature hành vi được dùng cho cả selector và learner; đây là deviation so với O17/QĐ3. Adapter hiện đã tách hai view: selector dùng 56 feature hành vi không có mã; learner dùng 62 feature, giữ `learner_code`, `teacher_set_code`, `school_set_code`, `field_set_code`, `gender_code` và `phase_fraction`. Các số screening bên dưới phải chạy lại theo view mới.

Nhãn chính là `y_alpha_1`, ánh xạ `E=0`, `G=1`, `A=2`. Phân bố dev rất lệch: lớp 0 chỉ có 177/31.028 dòng ở mỗi phase, trong khi train có 7.920/248.652 dòng ở mỗi phase. Đây là một thay đổi prior đáng kể giữa train và dev, do đó báo cáo không chỉ dùng Macro-F1 mà phải theo dõi riêng recall, F1 và PR-AUC của lớp 0.

Thiết kế screening lịch sử tại commit `46f733a`:

- split: development-only, test khóa;
- learner: XGBoost, model seed 42;
- selector seed: 11, 29, 47;
- ngân sách: 2%, tương đương 19.892 dòng, nén xấp xỉ 50 lần;
- cấu hình: FullTrain-B, C02, C03, SKQ-PC, SKQ-PC-LRQ-SQ và SKQ-PC-R;
- một mô hình đã fit được tái sử dụng để đánh giá bốn phase dev;
- bốn phase là bốn thời điểm đánh giá theo thời gian, không phải bốn lần lặp độc lập.

## 3. Phản hồi các vấn đề nghiêm trọng

### R1 Bài toán của đề tài chưa được thực nghiệm

**Trạng thái: đã có bằng chứng development, chưa đóng hoàn toàn.**

CQ v1 đã được đăng ký trong pipeline, tạo Pool B bốn phase và chạy screening trên dev. Đây là lần đầu có kết quả thực nghiệm đúng dữ liệu chính thay cho Adult hoặc CQ_med. Tuy nhiên, snapshot vẫn dùng `course_id` làm group tạm thời và chưa có `course_root_id`; endpoint cấp khóa học chưa được tính. Vì vậy R1 được chuyển từ “chưa thực nghiệm” sang “đã có development evidence, chưa đủ confirmatory”.

### R2 Phương pháp đề xuất chưa có bằng chứng tác dụng và tính mới chưa được bảo vệ

**Trạng thái: có tín hiệu development nhưng chưa chứng minh ưu thế.**

Ba candidate SKQ-PC theo review đã chạy ở cùng budget. LRQ-SQ có MCC và loss tốt nhất trong nhóm nén, nhưng không hơn C03 về Macro-F1 và làm giảm recall lớp hiếm. SKQ-PC chuẩn không đạt screening; SKQ-PC-R chỉ có lợi thế ở một số chỉ số ranking. Tính mới và claim cuối cùng vẫn phải phụ thuộc vào ablation cơ chế và kết quả đa learner/confirmatory.

## 4. Phản hồi các vấn đề quan trọng

| ID | Yêu cầu chính | Việc đã làm và bằng chứng | Trạng thái hiện tại |
|---|---|---|---|
| O1, O13 | CQ v1 ở cấp lượt ghi danh, Pool B và split theo khóa | Adapter CQ v1 đọc Parquet P1-P4; Pool B 994.608 dòng; train/dev/test không giao nhau theo `course_id` tạm thời | Một phần; thiếu `course_root_id` và data card hoàn chỉnh |
| O2 | Nhiều selector seed, ghi rõ split | Đã chạy seed 11, 29, 47; mọi dòng kết quả ghi `dev_phase1` đến `dev_phase4` | Đạt cho screening; chưa phải five-seed confirmatory |
| O3 | So sánh cùng budget, không kết luận non-inferiority từ point estimate | C02, C03 và ba SKQ candidate đều có đúng 19.892 dòng; native/FullTrain không bị giả làm exact-budget | Đạt cho mô tả; kiểm định và CI chưa chạy |
| O4 | Synthetic bất thường | Synthetic bị loại khỏi phạm vi CQ chính và config audit chặn gọi nhầm | Đã xử lý |
| O5 | Thiếu baseline hiện đại và kernel | Fidelity G10 trên Kaggle T4 đạt 10/10 toy; source/commit/interface đã khóa | Đạt fidelity; chưa phải benchmark hiệu năng CQ |
| O6 | Phạm vi quá rộng | CQ là dữ liệu chính; screening chỉ dùng panel thu gọn và ba candidate SKQ | Đã thu hẹp |
| O7 | Thiếu nguồn gốc và phiên bản nhãn CQ | Manifest lưu target `y_alpha_1`, mapping lớp, hash file và preprocessing | Một phần; data card vẫn cần mô tả công thức và quy ước nghiệp vụ đầy đủ |
| O8, O15 | Chưa chứng minh động lực chi phí; operation gate chưa hiệu chuẩn | Operation estimate đã chuyển thành diagnostic; thực nghiệm ghi selection/fit/total time và RSS lower bound | Một phần; còn thiếu calibration 50k/200k/800k x 3 |
| O9 | Khảo sát prior art chưa đủ | Chưa cập nhật trong vòng screening này | Chưa hoàn tất |
| O10 | Không truy cập được code và kết quả thô | Repo/branch/commit, config, run ledger, per-label metrics và confusion matrix đã có | Đạt cho development; nhánh chưa hợp vào main |
| O11 | Đánh đổi prior giữa hai endpoint | Effective weight được chuẩn hóa mean-one; class-mass diagnostics có trong method artifact | Một phần; chưa có EC và A8 |
| O12 | Khóa lớn chi phối và khóa nhỏ nhiễu | Hạ tầng course metrics/bootstrap đã có | Chưa thể xác nhận do thiếu `course_root_id` và chưa chạy endpoint cấp khóa học |
| O14, QĐ15 | Chuẩn hóa thang trọng số | Effective weight = method weight x class weight, sau đó chuẩn hóa mean-one cho mọi run type | Đã triển khai và kiểm thử; cần đưa evidence vào báo cáo run |
| O16 | Tune và early stopping trên dev | XGBoost dùng early stopping trên dev, best iteration được lưu | Đạt cho XGBoost screening; panel learner khác chưa chạy |
| O17 | ID không làm tọa độ selector; learner giữ mã tĩnh QĐ3 | Adapter mới: selector 56 feature không mã, learner 62 feature có năm mã tĩnh; test dual-view đã qua | Code đạt; screening cũ lệch giao thức và phải chạy lại |
| O18, QĐ17 | Privacy, version, tag và PR | Dữ liệu/Kaggle để private; tag review đã có; audit ghi nhận workbook nhị phân còn trong Git history | Chưa đóng G01; nhánh `cq-v1-protocol-fixes` chưa nằm trong `main` và cần quyết định xử lý history |

## 5. Phản hồi các quyết định bổ sung ngày 13 tháng 10

### QĐ12 Ngân sách theo headroom

Đã chạy lại headroom trên dev bằng đúng FullTrain-B và C02 tại bốn mức `0,5%`, `1%`, `2%` và `5%`, với selector seed `11, 29, 47`. Lượt chạy dùng XGBoost, class-weight tự nhiên, gom bốn phase bên trong từng seed và không đọc metric test. FullTrain-B đạt UL `0,654338`. Không mức nào đạt ngưỡng chênh lệch đăng ký `0,01`, nên quy tắc fallback chọn mức nhỏ nhất `rho*=0,5%`. Quyết định `2%` ở vòng cũ bị supersede và không còn là đầu vào hợp lệ cho QĐ16 hay lượt chọn phương pháp tiếp theo.

| Ngân sách | UL C02 trung bình ba seed | FullTrain-B trừ C02 | Đạt ngưỡng 0,01 |
|---:|---:|---:|:---:|
| 0,5% | 0,650153 | 0,004185 | Không |
| 1% | 0,655179 | -0,000842 | Không |
| 2% | 0,647283 | 0,007055 | Không |
| 5% | 0,652001 | 0,002337 | Không |

Kết quả có độ biến thiên đáng kể giữa ba selector seed, vì vậy bảng trên chỉ là quyết định giao thức theo quy tắc đã đăng ký, không phải tuyên bố rằng `0,5%` tốt hơn mọi mức còn lại. Quyết định này cũng chưa phải freeze M1 vì còn thiếu group-unit confirmation và các gate M0 khác.

### QĐ13 Xử lý test đã mở

Kết quả CQ_med cũ được giữ là exploratory. CQ v1 screening lịch sử và lượt headroom hiện hành đều chỉ dùng dev; các file test có trong snapshot nhưng runner không đánh giá test khi chưa có freeze hợp lệ. Không sử dụng test để chọn candidate, budget hoặc baseline.

### QĐ14 CoreTab XGB OVA adapted

Adapter OVA, largest-remainder quota, no-padding và realized-size diagnostics đã được cài đặt và kiểm thử. G10 chỉ xác minh fidelity/interface. CoreTab OVA chưa được benchmark trên CQ v1 tại ngân sách mới `rho*=0,5%`, nên chưa có số liệu hợp lệ để so sánh với SKQ-PC.

### QĐ15 Trọng số huấn luyện

Pipeline đã chuẩn hóa effective sample weights về mean 1. FullTrain-B đã so sánh natural với balanced trên UL và EC provisional: natural XGBoost hiện tốt nhất đồng thời trước A8 (`UL=0,654338`, `EC=0,080661`), trong khi A8 giúp balanced XGBoost giảm EC nhưng làm giảm UL. Chính sách natural vẫn ghi `provisional_pending_supervisor_confirmation`; LR chưa được dùng để chốt vì cả tám fit cũ đều chạm `max_iter=5000` và phải tune lại dev-only.

### QĐ16 Cổng tài nguyên theo thời gian đo

Ngưỡng số phép tính cũ không còn dùng để loại phương pháp. Lượt calibration lịch sử đã đo ba candidate tại `rho=2%`, nhưng QĐ12 hiện đã chốt `rho*=0,5%`; vì vậy các số `2%` chỉ còn là evidence lịch sử. G09 chỉ đạt sau khi đo đủ 10 selector cố định và ba candidate tại `rho*=0,5%`, ba cỡ `50k/200k/800k`, ba replicate, rồi tính lịch dev/test từ upper prediction bound.

Checkpoint QĐ16 mới tại `rho*=0,5%` đã hoàn tất 9/13 phương pháp, mỗi phương pháp đủ ba cỡ và ba replicate; 17/17 kiểm thử QĐ16 đạt, test CQ không được đọc. Chín phương pháp hoàn tất đều có upper prediction dưới trần ba giờ. Trong số này CoreTab-XGB OVA có upper prediction lớn nhất (`5.216,48 s`, khoảng 87 phút), tiếp theo là GCoreSet (`2.128,58 s`) và Data-OOB (`593,04 s`). Data-OOB có upper peak RSS khoảng `20,82 GiB`, cần giữ trong báo cáo tài nguyên dù thời gian đạt trần.

Archive được đóng gói trước khi Kernel Thinning bắt đầu nên không chứa checkpoint Kernel Thinning; không được suy diễn các dòng log ngoài archive thành run thành công. Các phương pháp còn thiếu là Kernel Thinning và ba candidate SKQ. Vì vậy QĐ16 hiện là `PARTIAL`, chưa sinh được lịch dev/test đầy đủ.

### QĐ17 Chia sẻ và phiên bản

Repo và notebook đã chuyển private. Tag `review-2026-10-13` tồn tại tại mốc lịch sử đã gửi. Nhánh protocol hiện chưa được hợp vào `main`; G01 vẫn chưa đạt do ba Git object của workbook nhị phân còn trong history. Nhóm chưa rewrite history để tránh làm mất các commit/tag đã chia sẻ; cần giảng viên hoặc nhóm chọn repo public sạch từ allowlist hay phê duyệt rewrite.

## 6. Kết quả screening CQ v1 lịch sử ở ngân sách 2 phần trăm

Phần này được giữ để truy vết failure mode và lý do sửa pipeline. Nó không còn là bảng chọn candidate sau khi QĐ12 mới chốt `rho*=0,5%`.

### 6.1 Kết quả tổng thể

| Phương pháp | Macro-F1 | MCC | Balanced accuracy | Worst-class recall | PR-AUC macro | Log loss | Tổng thời gian giây |
|---|---:|---:|---:|---:|---:|---:|---:|
| FullTrain-B | 0,5802 | 0,5834 | 0,7030 | 0,5268 | 0,6862 | 0,5243 | 17,9 |
| C02 stratified random | 0,5649 | 0,5588 | 0,6405 | 0,3630 | 0,6617 | 0,5399 | 1,8 |
| C03 phase-class random | 0,5862 | 0,5869 | 0,6302 | 0,2943 | 0,6595 | 0,5049 | 3,7 |
| SKQ-PC | 0,5552 | 0,5679 | 0,6273 | 0,3150 | 0,6772 | 0,5501 | 248,0 |
| SKQ-PC-LRQ-SQ | 0,5860 | 0,6070 | 0,6258 | 0,2599 | 0,6537 | 0,4878 | 258,3 |
| SKQ-PC-R | 0,5785 | 0,5813 | 0,6189 | 0,2698 | 0,6766 | 0,5150 | 60,4 |

Các giá trị là thống kê mô tả trên các dòng đánh giá dev phase và selector seed. Không dùng bốn phase như bốn replicate độc lập để tính p-value.

### 6.2 So sánh cặp quan trọng

So với C02, LRQ-SQ tăng Macro-F1 khoảng 0,0211 và MCC khoảng 0,0482, đồng thời giảm log loss khoảng 0,0521. Tuy nhiên, worst-class recall giảm khoảng 0,1031.

So với C03, LRQ-SQ gần như hòa Macro-F1, tăng MCC khoảng 0,0201, nhưng giảm worst-class recall khoảng 0,0344 và tốn tổng thời gian khoảng 70 lần. Vì vậy chưa thể nói LRQ-SQ vượt C03 một cách toàn diện.

SKQ-PC chuẩn thấp hơn C02 khoảng 0,0097 Macro-F1 và thấp hơn C03 khoảng 0,0310. SKQ-PC-R tốt hơn C02 về Macro-F1 nhưng thấp hơn C03 khoảng 0,0077 và cũng giảm recall lớp hiếm.

### 6.3 Kết quả lớp hiếm

| Phương pháp | Precision lớp 0 | Recall lớp 0 | F1 lớp 0 | PR-AUC lớp 0 |
|---|---:|---:|---:|---:|
| FullTrain-B | 0,1346 | 0,5268 | 0,2144 | 0,2816 |
| C02 | 0,1435 | 0,3630 | 0,1983 | 0,2222 |
| C03 | 0,1787 | 0,2943 | 0,2137 | 0,2032 |
| SKQ-PC | 0,1156 | 0,3150 | 0,1655 | 0,1886 |
| SKQ-PC-LRQ-SQ | 0,1755 | 0,2599 | 0,1994 | 0,1231 |
| SKQ-PC-R | 0,1925 | 0,2698 | 0,2127 | 0,2037 |

Không có candidate SKQ nào giữ recall lớp 0 tốt hơn C02 hoặc FullTrain-B. LRQ-SQ cải thiện MCC/loss chủ yếu nhờ lớp 1 và lớp 2. Đây là failure mode phải được xử lý trước khi giữ claim bảo toàn lớp hiếm hoặc bảo toàn prior.

## 7. Quyết định development sau screening

1. Giữ `SKQ-PC-LRQ-SQ` làm ứng viên chính tạm thời vì có MCC và loss tốt nhất trong nhóm nén.
2. Không chọn `SKQ-PC` chuẩn làm phương pháp chính; giữ như ablation gốc.
3. Giữ `SKQ-PC-R` như ablation về random-in-cell hoặc ranking-AUC, không xem là winner.
4. Giữ C03 là baseline bắt buộc vì rất nhanh và ngang LRQ-SQ về Macro-F1.
5. Chưa loại C02 vì đây là đối chứng mạnh nhất về recall lớp hiếm trong nhóm nén.
6. Chưa mở test, chưa chạy kiểm định confirmatory và chưa sử dụng từ “vượt trội” hoặc “SOTA”.

## 8. Các gate hiện tại

| Gate | Trạng thái | Bằng chứng hoặc blocker |
|---|---|---|
| G00 Scope | Đạt cho config screening | Chỉ CQ v1 và panel thu gọn |
| G01 Privacy | Chưa đạt | Workbook nhị phân còn trong Git history |
| G02 Data schema | Đạt một phần | Enrollment-phase schema có hash; data card chưa hoàn chỉnh |
| G03 Split | Chưa đạt confirmatory | Disjoint theo `course_id`; thiếu `course_root_id` |
| G04 Labels and course metrics | Một phần | FullTrain-B đã có UL/EC provisional, ICC và oracle floor; còn chờ chốt group unit và FullTrain-A |
| G05 Cutoff | Chưa có evidence đầy đủ | Cần 20 ca kiểm thủ công |
| G06 Weights | Đạt ở code và screening | Mean-one effective weights; cần manifest run rõ hơn |
| G07 Views | Đạt | Feature contract loại ID và target-derived columns |
| G08 Learner | Đạt cho XGBoost, LR còn mở | XGBoost early stopping dev-only; LR cũ không hội tụ, cần tuning tối đa tám cấu hình |
| G09 Resource | Một phần (9/13) | 9 selector đủ 50k/200k/800k x 3 tại `rho*=0,5%`; còn Kernel Thinning và 3 candidate, chưa có lịch dev/test đầy đủ |
| G10 Fidelity | Đạt | Kaggle T4 strict toy 10/10 |
| G11 SKQ-PC | Đạt contract cơ bản | Exact budget, class coverage và mass error đạt; thiếu cờ QP rõ trong evidence hiện tại |
| G12 CoreTab OVA | Đạt unit/fidelity, chưa có CQ benchmark | Chưa chạy tại `rho*=0,5%` |
| G13 Statistics | Một phần | Protocol có; chưa có bootstrap đúng course root |
| G14 Freeze M0 | Chưa đạt | Thiếu group unit/raw checks, FullTrain-A, LR hợp lệ và G09 tại rho mới |
| G15 Freeze M1 | Chưa đạt | Chưa chọn candidate cuối và chưa đủ evidence |
| G16 Reporting | Một phần | Có run_id/config/split/commit; còn thiếu một số field chi phí và QP |

## 9. Công việc tiếp theo đã chốt

### 9.1 Sửa evidence pipeline trước khi chạy thêm

- Ghi `passes_over_train` cho từng selector và phân biệt exact, lower bound hoặc unknown.
- Ghi trực tiếp `qp_converged` và `qp_constraint_valid` vào artifact SKQ-PC.
- Ghi rõ selection time, fit time và total time chỉ một lần cho model được tái sử dụng qua bốn phase; không cộng lặp bốn dòng phase.
- Bổ sung GPU telemetry hoặc ghi `not_measured`; không dùng giá trị 0 như bằng chứng không dùng VRAM.
- Giữ method artifact tách khỏi evaluation table và tiếp tục xuất per-label metrics/confusion matrix.

### 9.2 Chạy ablation development về lớp hiếm

Không mở test. Sau khi hoàn tất panel M0 tối thiểu tại `rho*=0,5%`, nếu còn thời gian dev thì tách ảnh hưởng của LRQ và SQ tại cùng ngân sách và ba seed:

1. LRQ với uniform method weights;
2. SQ không LRQ;
3. LRQ-SQ với minimum quota hoặc loss allocation tăng cho lớp 0;
4. C02 và C03 giữ nguyên làm đối chứng.

Tiêu chí giữ sửa đổi: Macro-F1/MCC không giảm đáng kể so với LRQ-SQ hiện tại, đồng thời recall lớp 0 tăng nhất quán qua selector seed và phase. Không chọn cấu hình bằng test.

### 9.3 Hoàn thiện các blocker review

- Xin hoặc xác nhận ánh xạ `course_id -> course_root_id`; nếu không tồn tại khóa mở lại, cần văn bản xác nhận để khóa group unit.
- Chạy endpoint cấp khóa học UL/EC, ICC và oracle floor sau khi group unit được chốt.
- Chạy CoreTab-XGB OVA adapted ở `rho*=0,5%` trên dev.
- Chạy resource calibration theo QĐ16 cho đủ 10 selector cố định và ba candidate tại `rho*=0,5%`.
- Chốt natural/balanced class weights trên dev theo cả UL và EC.
- Hoàn thiện data card, privacy decision và freeze manifest trước khi mở test.

## 10. Các câu hỏi cần giảng viên xác nhận

1. Dữ liệu hiện không có `course_root_id`. Nếu mỗi `course_id` đã là một khóa gốc duy nhất và không có lần mở lại, có thể dùng `course_id` làm group unit confirmatory hay cần bổ sung cột xác nhận riêng?
2. Có cho phép nhóm giữ LRQ-SQ làm candidate chính và dùng một vị trí ablation để thử minimum allocation cho lớp hiếm, miễn tổng candidate dùng để chọn trên dev không vượt ba?
3. Khi LRQ-SQ tăng MCC/loss nhưng không hơn C03 về Macro-F1 và kém recall lớp hiếm, cô ưu tiên hướng sửa phương pháp hay chuyển đóng góp sang empirical benchmark/negative result?
4. Với privacy history finding, cô ưu tiên tạo repo public sạch từ allowlist hay tiếp tục giữ repo hiện tại private đến khi nộp?
5. Giai đoạn tiếp theo có cần mở rộng ngay sang LR/RF hay hoàn tất endpoint cấp khóa học, CoreTab OVA và resource calibration với XGBoost trước?

## 11. Tài liệu và evidence đi kèm

- Review ngày 12/10/2026 và Review ngày 13/10/2026.
- Kế hoạch thực hiện V2 và ma trận traceability Review 12-13.
- Evidence G10 fidelity trên Kaggle T4, strict audit 10/10.
- Archive headroom CQ v1 trên dev: `results/cq_v1/skq_cq_v1_m0_headroom_2026_10_21.tar.gz`, SHA-256 `2839B7D1AF1284999DD1AC1ED406058A9D875E7048A5FB77E2C82AD3EE4EE4A3`; 52/52 evaluation thành công, 54/54 pytest đạt, chọn `rho*=0,5%` bằng fallback đã đăng ký.
- Quyết định máy đọc: `docs/cq_v1/m0_headroom_decision_2026_10_21.json`, SHA-256 `623A22DC40ABBF19A48860CC72E884F0E409447F7CDC0380EE3575853A5C0DC9`.
- Archive QĐ16 partial: `results/cq_v1/skq_cq_v1_m0_qd16_resource_rhostar.tar.gz`, SHA-256 `83BEAA285714AB642B722DFDC9E816B38193833D9FB44F73E39E17218D04ECAA`; 9/13 phương pháp hoàn tất, 17/17 pytest đạt, không có metric test.
- Archive screening CQ v1 lịch sử ở 2%, seed 11/29/47; không dùng làm quyết định headroom hoặc QĐ16 hiện hành.
- Các bảng `metrics_overall_long.csv`, `metrics_per_label_long.csv`, `confusion_matrix_long.csv`, run ledger và method artifacts trong archive screening.

## 12. Giới hạn diễn giải

Các số screening sáu phương pháp ở Mục 6 là development evidence lịch sử ở learner view 56 feature và đã bị supersede cho mục đích chọn candidate. Riêng headroom QĐ12 tại commit `9b07f6f` là evidence dual-view hiện hành để chốt `rho*=0,5%`, nhưng không tự động làm M0 đạt GO. Không sử dụng bất kỳ số nào để tuyên bố hiệu quả trên test, không coi phase là replicate độc lập, không gọi phương pháp là SOTA và không dùng kết quả để thay đổi test split.
