# Novelty ledger M0 — chưa dùng để tuyên bố tính mới

**Trạng thái:** khung kiểm tra, chưa hoàn tất tìm kiếm hệ thống.

**Ngày cập nhật:** 21/10/2026.

| Cụm tài liệu | Câu hỏi đối chiếu | Evidence phải lưu | Trạng thái |
|---|---|---|---|
| Early course-quality prediction | Đã có phương pháp chọn tập huấn luyện theo ngân sách cho P1–P4 và hai endpoint UL/EC chưa? | Query, nguồn, DOI/URL, trích yếu claim | Chưa hoàn tất |
| CoreTab và tabular coreset | CoreTab gốc hỗ trợ binary/multiclass thế nào; OVA hiện là adapted baseline hay đóng góp? | Paper/code/version và fidelity test | Một phần; CoreTab-OVA giữ nhãn adapted |
| Kernel thinning/Compress++ | Có bảo đảm kernel-mean nào phù hợp dữ liệu bảng/multiclass? | Định lý, giả định, độ phức tạp | Chưa hoàn tất |
| Dataset condensation | Các baseline hiện đại có cùng output contract và learner-agnostic không? | Paper/code/license/fidelity | Fidelity G10 đạt; benchmark CQ chưa đủ |
| Imbalanced multiclass selection | Class allocation, mass preservation và rare-class recall đã được xử lý ra sao? | Prior work và khác biệt cơ chế | Chưa hoàn tất |

## Quy tắc kết luận

- Không dùng từ “novel”, “SOTA” hoặc “đầu tiên” khi ledger chưa hoàn tất.
- OVA của CoreTab là baseline thích nghi theo QĐ14, không tự động là đóng góp mới.
- Claim phương pháp chỉ được viết sau khi một candidate vượt gate dev và được freeze.
- Kết quả âm hoặc trade-off vẫn phải báo, không xóa candidate sau khi nhìn test.
