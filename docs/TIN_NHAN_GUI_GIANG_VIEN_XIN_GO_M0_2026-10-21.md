# Tin nhắn xin duyệt GO M0 có điều kiện

Thưa cô,

Nhóm đã chuyển pipeline sang CQ V3 và hoàn tất phần bằng chứng M0 có thể kiểm
tra trên train/dev. Gói chạy M0 không chứa test parquet và dataset Kaggle được
đặt Private. Pipeline dùng split không trùng course, tiền xử lý chỉ fit trên
Pool B train, dùng một model đánh giá lại trên bốn phase, lưu prediction và báo
cả UL/EC, metric theo lớp, thời gian cùng bộ nhớ.

Các kiểm tra đã có bằng chứng trực tiếp gồm: 61 kiểm thử protocol; course-ID
probe không hơn majority; missingness probe chỉ dùng chẩn đoán; 20/20 ca cutoff
private không có event vượt cửa sổ; kiểm tra đơn vị, nhãn, feature allowlist,
course recompute và các hằng số protocol đều đạt. Cell Kaggle T4 đang chạy phần
shuffled-label, FullTrain-B tự nhiên/cân bằng với LR và XGB, cùng headroom
0,5/1/2/5% trên ba selector seed. Test vẫn khóa.

Nhóm xin **GO M0 có điều kiện để tiếp tục M1 trên train/dev và hoàn thiện bản
thảo**, đồng thời xin cô xác nhận năm điểm:

1. Có thể dùng `course_id` làm group unit nếu phía dữ liệu xác nhận mỗi course
   chỉ mở một lần không?
2. Có chấp thuận split random 70/10/20 theo course cho M1, hay cần đổi sang
   temporal/SGKF?
3. FullTrain-A nên được cung cấp thêm nguồn full-behavior, được miễn, hay dùng
   một định nghĩa thay thế do P4 hiện chỉ đến 90%?
4. Kernel Thinning có thể ghi timeout/censored theo trần tài nguyên và vẫn cho
   phép sang M1 khi ba candidate còn lại hoàn tất không?
5. Dataset Kaggle Private và repo Private có đủ cho M0, hay phải xử lý ba object
   XLSX còn trong Git history trước khi tiếp tục?

Nhóm chưa xin mở test, chưa chốt candidate và chưa đưa ra claim SOTA/tính mới.
Khi notebook V3 kết thúc, nhóm sẽ gửi kèm archive bất biến, SHA-256, commit code,
bảng headroom và bảng trạng thái từng gate.

Tài liệu kèm theo:

- `docs/BAO_CAO_XIN_GO_M0_V3_2026-10-21.md`
- `docs/CQ_V3_M0_GO_CHECKLIST_2026-10-21.md`
- `paper/icc_review_m0_v1/main.tex`
- archive Kaggle V3 và checksum (bổ sung ngay sau khi run hoàn tất)
