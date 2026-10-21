# CQ v1 — Checklist GO M0 ngày 21/10/2026

## Quy tắc dữ liệu

- M0 chỉ dùng train và dev để chọn giao thức.
- Được kiểm tra metadata/phân bố/hash của test để audit split, nhưng không fit,
  dự đoán, tính metric, chọn tham số hoặc sửa candidate từ test.
- Mọi config M0 giữ `test_locked=true`; test chỉ mở sau M1 freeze hợp lệ.

## Bốn điều kiện GO theo Review 12–13/10

| Điều kiện | Trạng thái 21/10 | Evidence hiện có | Việc còn thiếu để GO |
|---|---|---|---|
| Data card, split và checks 1–7, 9–12 | PARTIAL | `docs/cq_v1/M0_DATA_CARD_PROVISIONAL.md`; D01, D02, D04, D05, D07, D09–D12 có evidence; headroom suite 54/54 PASS | Xác nhận `course_id == course_root_id`; D03 missingness và D06 cutoff-20 cần raw data |
| FullTrain-A/B dev, LR/XGB, UL/EC, natural/balanced | PARTIAL | Bốn ô FullTrain-B và UL/EC provisional đã có; natural XGB tốt nhất trước A8 | FullTrain-A bị chặn vì thiếu full-behavior table; LR cũ không hội tụ, cần tuning dev-only; EC chờ chốt group unit |
| Timing chứng minh phạm vi hoàn tất đúng hạn | PARTIAL 9/13 | Chín selector đã đủ 50k/200k/800k × 3 tại `rho*=0,5%`; QĐ16 pytest 17/17 PASS | Khôi phục archive đã kiểm kê; xử lý Kernel Thinning có timeout và chạy 3 candidate; tính upper-bound schedule dev/test |
| Khung bài Introduction/Related Work/Problem/Data | PARTIAL | `paper/icc_review_m0_v1/main.tex` compile thành công và đã có bảng headroom dev-only | Introduction/Related Work/Problem/Data vẫn còn placeholder, nhóm tác giả phải điền nội dung thật; chưa viết claim test |

## Số liệu data card cần giảng viên chốt

- Train/dev/test có 1.902/266/512 khóa theo `course_id`, không giao nhau.
- `n_min=30` chỉ là tạm thời. Dev có 61/266 khóa đủ `n_min`; 205 khóa bị loại.
- ICC(1) q theo khóa: train 0,267405; dev 0,460239; test 0,442543.
- Train-only constants: `mu_E=0,07373661`, `mu_G=0,32728126`,
  `mu_A=0,64609105`, đúng thứ tự và đúng dải lớp.
- Oracle-floor EC dev tại `n_min=30`: 0,05878932 trên 61 khóa.
- Vì oracle floor đã lớn hơn `delta_C=0,01`, cần cô xác nhận có giữ `delta_C`
  hay sửa tại M0; nhóm không tự đổi sau M0.

## Thứ tự chạy trong hơn 20 giờ còn lại

1. Chạy LR tuning dev-only tối đa tám cấu hình; không dùng LR cũ chưa hội tụ để chốt policy.
2. Khi có xác nhận root, khóa UL/EC bằng PCC và CC sensitivity. Số hiện tại theo
   `provisional_course_id` không phải confirmatory evidence.
3. Chạy resource calibration QĐ16 trên Kaggle T4 tại `rho*=0,5%`; không giảm ba replicate và không tái sử dụng bảng 2% làm quyết định chính.
4. Tổng hợp M0 packet: data card, checks, FullTrain table, endpoint table,
   resource decision, paper skeleton, commit/tag và danh sách blocker.
5. Không chạy selector bảng chính mới, không mở test, không freeze M1 ở M0.

Lưu ý: screening commit `46f733a` dùng 56 feature cho cả learner và selector,
không đúng O17/QĐ3. Chỉ các run từ commit dual-view trở đi mới được dùng cho
quyết định M0/M1; số cũ giữ như evidence chẩn đoán, không xóa.

Headroom dual-view tại commit `9b07f6f` đã hoàn tất 52/52 evaluation và 54/54
pytest, chọn `rho*=0,5%` bằng fallback đăng ký. Đây là PASS cho bước chọn ngân
sách QĐ12, không phải PASS cho toàn M0.

## Blocker cần phản hồi ngoài code

1. Xác nhận bằng văn bản mỗi `course_id` chỉ có một lần mở, hoặc cung cấp
   `course_root_id`.
2. Cung cấp raw/pre-imputation features để chạy missingness probe D03.
3. Cung cấp raw event timestamps để lấy 20 ca cutoff audit D06.
4. Cung cấp FullTrain-A/full-behavior table hoặc xác nhận P4 có được xem là
   FullTrain-A hay không; nhóm hiện không tự xem P4=90% là full behavior.
5. Chốt `n_min` và `delta_C` dựa trên data card/oracle floor.

## Tiêu chí gửi “GO/NO-GO M0” trung thực

- **GO M0 đầy đủ:** bốn điều kiện review đều có evidence và không còn blocker
  giao thức bắt buộc.
- **GO có điều kiện:** code, dev runs, timing và skeleton đủ nhưng còn xác nhận
  root/raw audit từ nhóm dữ liệu; ghi rõ điều kiện, không mở test.
- **NO-GO:** dùng test để bù evidence thiếu, giả P4 là FullTrain-A, hoặc tự đổi
  `n_min`/`delta_C` mà không ghi deviation.
