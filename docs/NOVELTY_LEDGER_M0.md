# Novelty ledger M0 — chưa dùng để tuyên bố tính mới

**Trạng thái:** đã xác minh ba nguồn lõi; tìm kiếm hệ thống theo miền ứng dụng và
imbalanced multiclass vẫn chưa hoàn tất.

**Ngày cập nhật:** 21/10/2026.

| Cụm tài liệu | Câu hỏi đối chiếu | Evidence phải lưu | Trạng thái |
|---|---|---|---|
| Early course-quality prediction | Đã có phương pháp chọn tập huấn luyện theo ngân sách cho P1–P4 và hai endpoint UL/EC chưa? | Query, nguồn, DOI/URL, trích yếu claim | Chưa hoàn tất |
| CoreTab và tabular coreset | CoreTab gốc hỗ trợ binary/multiclass thế nào; OVA hiện là adapted baseline hay đóng góp? | Repo `avivhadar33/coretab`, khóa commit `74edad5129e0ada98d9f04150ab9ffdb6773c5fc`; fidelity test | Đã xác minh nguồn phần mềm; giao diện gốc là binary, OVA phải ghi `adapted baseline`, không phải đóng góp |
| Kernel thinning/Compress++ | Có bảo đảm kernel-mean nào phù hợp dữ liệu bảng/multiclass? | Dwivedi--Mackey, JMLR 25 (2024), bài 21-1334; giả định, độ phức tạp và implementation label | Đã xác minh bảo đảm nén phân phối/RKHS; chưa có căn cứ chuyển trực tiếp thành bảo đảm utility supervised tabular; bản classwise là adaptation |
| Dataset condensation | Các baseline hiện đại có cùng output contract và learner-agnostic không? | Zhao--Mopuri--Bilen, ICLR 2021/OpenReview; paper/code/license/fidelity | Đã xác minh phương pháp sinh dữ liệu tổng hợp bằng gradient matching, khác contract chọn source rows; fidelity G10 đạt nhưng benchmark CQ chưa đủ |
| Imbalanced multiclass selection | Class allocation, mass preservation và rare-class recall đã được xử lý ra sao? | Prior work và khác biệt cơ chế | Chưa hoàn tất |

## Quy tắc kết luận

- Không dùng từ “novel”, “SOTA” hoặc “đầu tiên” khi ledger chưa hoàn tất.
- OVA của CoreTab là baseline thích nghi theo QĐ14, không tự động là đóng góp mới.
- Kernel Thinning không được mô tả là baseline có bảo đảm supervised utility;
  bảo đảm được trích dẫn chỉ thuộc nén phân phối/kernel mean dưới các giả định
  của bài gốc.
- Dataset condensation sinh điểm tổng hợp nên không được nhập chung với bảng
  selector trả source-row indices nếu không tách rõ output contract.
- Claim phương pháp chỉ được viết sau khi một candidate vượt gate dev và được freeze.
- Kết quả âm hoặc trade-off vẫn phải báo, không xóa candidate sau khi nhìn test.
