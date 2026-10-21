# Báo cáo xin GO M0 có điều kiện — CQ V3

**Ngày:** 21/10/2026  
**Nhánh:** `cq-v1-protocol-fixes`  
**Commit pipeline V3:** `81e1181a8ca25b0dceb9c387a3e3811a6f2d3466`  
**Phạm vi:** development-only; test bị loại khỏi gói chạy.

## 1. Kết luận đề nghị

Nhóm đề nghị giảng viên cho **GO M0 có điều kiện** để tiếp tục M1 trên train/dev
và hoàn thiện bản thảo LNCS. Đây chưa phải đề nghị mở test hay xác nhận phương
pháp cuối cùng.

Lý do có thể tiếp tục: pipeline CQ V3 đã có Pool B chung đúng feature contract,
probe missingness và cutoff đã chạy được, cấu hình FullTrain-B/headroom V3 đã
khóa, code đã qua 61 kiểm thử, và test parquet bị loại vật lý khỏi bundle M0.

Điều kiện còn chờ duyệt: group unit, deviation split ngẫu nhiên theo course,
FullTrain-A, và phần còn thiếu của timing QĐ16. Nhóm không tự suy diễn các điểm
này thành PASS.

## 2. Dữ liệu CQ V3 dùng cho M0

V3 loại 129.400 cặp chỉ có chapter không xác định, còn 178.598 cặp có nhãn,
168.410 người học và 1.808 course. Target và công thức q của các cặp được giữ
không đổi so với V2.

Nhóm chọn biến thể `course_random_split`, không dùng split mặc định có course
overlap:

| Split | Course | Cặp user--course | User |
|---|---:|---:|---:|
| Train | 1.265 | 128.407 | 122.959 |
| Dev | 181 | 16.301 | 16.176 |
| Test khóa | 362 | 33.890 | 33.238 |

Course overlap giữa ba split bằng 0. Đây là random 70/10/20 theo course, không
phải temporal hoặc SGKF; vì vậy cần giảng viên phê duyệt deviation trước M1
freeze.

Mỗi cặp có bốn snapshot P1/P2/P3/P4 ở 25/50/75/90% cửa sổ. Pool B train có
513.628 snapshot; dev có 65.204 snapshot. Adapter mới fit một phép tiền xử lý
duy nhất trên Pool B train rồi áp cho cả bốn dev phase. Việc này sửa lỗi thiết
kế nguồn V3 fit scaler riêng phase làm `phase_fraction` mất thông tin.

## 3. Gói Kaggle tối thiểu và privacy

Gói `cq_v3_m0_dev.zip` có 104.580.461 byte, SHA-256
`9F60946C140B7E16EE1F9BB3D94FC21BBEC898F476BE669416EBD6E4C55995A6`.
Gói chỉ chứa train/dev model-ready, supervised-raw, cutoff audit, encoder,
course split/static metadata và provenance.

Gói không chứa test parquet, 10,4 triệu dòng feature shard, sequence, bảng stage,
target toàn cohort hoặc split mặc định. Dataset Kaggle dùng để chạy gói này phải
đặt **Private**. Cell từ chối chạy nếu phát hiện `test.parquet` hoặc file sai
hash.

## 4. Kiểm tra bắt buộc D01--D12

| Check | Trạng thái V3 | Evidence |
|---|---|---|
| D01 phân bố/split | PASS train/dev | Quy mô, class, 0 course overlap |
| D02 ID-only | PASS | Course-only Macro-F1 0,269207, bằng majority; dev course unseen |
| D03 missingness | PASS probe | AUC macro OVR trung bình 0,610703; mask không vào production X |
| D04 shuffled label | Chờ Kaggle T4 | Dùng XGB trên Pool B đã joint-preprocess |
| D05 majority | PASS | Tính riêng P1--P4 |
| D06 cutoff-20 | PASS private | 20/20 max event không vượt cutoff; 0 out-of-window |
| D07 weight contract | PASS code | Suite kiểm thử thực thi |
| D08 fidelity | DEFERRED M1 | Review cho phép hoàn tất trước M1 |
| D09 đơn vị/nhãn | PASS | Unique user--course--phase; nhãn cố định P1--P4 |
| D10 no-label-in-X | PASS | Target/ID bị loại theo allowlist |
| D11 course recompute | PASS generated | Qc/Yc tái tính từ enrollment q |
| D12 constants | PASS | mu theo train và đúng thứ tự lớp |

D03 cho thấy missingness có tín hiệu vừa phải, không phải bằng chứng được phép
thêm missing masks vào X. D06 dựa trên audit timestamp tổng hợp của V3 và giữ
danh sách ID trong artifact private.

## 5. FullTrain và headroom

Cell M0 V3 chạy bốn ô FullTrain-B natural/balanced x LR/XGB, xuất prediction
dev P1--P4, UL enrollment và EC course provisional. Đồng thời cell chạy
FullTrain-B natural XGB và C02 tại rho 0,5/1/2/5%, selector seed 11/29/47 để
chọn lại rho-star trên V3.

Không tái sử dụng số utility V2 để quyết định V3. FullTrain-A vẫn bị chặn vì
V3 không có bảng full-behavior theo TEMPO-DQ; P4 chỉ đến 90% và không được đổi
tên thành FullTrain-A.

## 6. Timing QĐ16

Evidence hiện có tại rho-star V2 0,5% hoàn tất 9/13 phương pháp ở 50k/200k/800k,
ba replicate. Kernel Thinning đã cho thấy thời gian rất lớn nhưng archive chưa
có censor record hoàn chỉnh; ba candidate SKQ ở lượt rho-star cũng chưa xong.
Do đó timing là `PARTIAL_9_OF_13`, không phải PASS.

Sau khi rho-star V3 được chọn, nhóm sẽ:

1. giữ lại fixed-N calibration nếu feature count và contract không đổi, ghi rõ
   đây là evidence chuyển giao về tài nguyên chứ không phải utility V3;
2. ghi Kernel Thinning là timeout/censored nếu vượt trần, không thay proxy;
3. hoàn tất ba candidate và tính upper-bound schedule cho dev bốn ngày/test ba
   ngày trước khi freeze M1.

## 7. Trạng thái khung bài

Bản LNCS đã có abstract ở mức protocol, Introduction, Related Work,
Problem/Data/Protocol, định nghĩa UL/EC, phạm vi baseline, chính sách tài nguyên
và giới hạn diễn giải. BibTeX chỉ chứa nguồn đã kiểm chứng. Claim phương pháp,
kết quả confirmatory và mọi tuyên bố vượt trội vẫn được khóa cho đến sau M1
freeze và một lần mở test hợp lệ.

## 8. Các quyết định xin giảng viên phản hồi

Xin cô phản hồi trực tiếp năm câu sau:

1. Chấp thuận `course_id` làm group unit nếu xác nhận mỗi course chỉ mở một lần?
2. Chấp thuận `course_random_split` cho M1, hay bắt buộc dựng temporal/SGKF?
3. Xử lý FullTrain-A theo hướng cung cấp nguồn, miễn baseline, hay duyệt định
   nghĩa thay thế?
4. Cho phép chuyển sang M1-dev khi Kernel Thinning được ghi timeout/censored và
   ba candidate hoàn tất, hay yêu cầu đủ 13 fitted scaling models?
5. Dataset Kaggle private cùng repo private có đủ cho M0, hay phải xử lý ba
   object XLSX trong Git history trước khi tiếp tục?

## 9. Đề nghị phê duyệt

Nếu các giới hạn trên được chấp thuận, nhóm xin phép:

- tiếp tục M1 trên train/dev;
- chạy panel baseline/candidate tại rho-star V3;
- hoàn thiện Introduction/Related Work/Method và novelty ledger;
- giữ test khóa cho đến khi có M1 freeze manifest được duyệt.

Nhóm không xin phép mở test tại M0 và không dùng kết quả hiện tại để tuyên bố
SOTA, vượt trội hoặc tính mới.
