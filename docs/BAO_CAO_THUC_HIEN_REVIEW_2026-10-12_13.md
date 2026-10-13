# Nhật ký thực hiện Review 12–13/10/2026

Tài liệu này dùng để thu hoạch những gì đã làm và phân biệt quyết định của giảng
viên với suy luận kỹ thuật của nhóm. Chưa có mục nào trong file này tự tạo bằng
chứng confirmatory.

## Quy ước

- **Xác nhận trực tiếp:** làm đúng câu chữ review; không cần diễn giải thành đóng
  góp mới.
- **Suy luận triển khai:** lựa chọn kỹ thuật không được review chỉ rõ; phải nêu lý
  do, rủi ro, test và phạm vi claim.
- **Bằng chứng:** commit, test, evidence manifest hoặc run ID; không dùng nhận xét
  miệng thay bằng chứng.

## Nhật ký

### 14/10/2026 — Khóa kế hoạch và metadata nền

**Xác nhận trực tiếp đã áp dụng**

- Giữ riêng các trạng thái `failed`, `oom`, `timeout`, `blocked`, `na_contract`,
  không đổi lỗi thành success và không loại khỏi ledger.
- Giữ provenance theo commit/hash, artifact identity và không fallback âm thầm.
- P01–P05, P09–P11 không được xem là phương pháp confirmatory mới.
- CoreTab native là binary-only; OVA phải mang nhãn adapted.
- Tổng số candidate SKQ-PC dùng chọn dev không vượt ba.

**Suy luận triển khai**

- Thêm taxonomy machine-readable thay cho chỉ ghi chú tự do trong registry.
- Đăng ký ý tưởng CoreTab multiclass dưới mã exploratory bị vô hiệu hóa, để có thể
  viết contract/test toy nhưng không thể đi vào config confirmatory trước khi được
  chấp thuận.
- Thêm `.editorconfig` UTF-8 để docstring tiếng Việt nhất quán Windows/Kaggle.

**Bằng chứng dự kiến**

- `tests/test_method_fidelity.py`.
- Commit của lát metadata sau khi test đạt.

## Mẫu cho các mục tiếp theo

```text
Ngày / requirement IDs:
Xác nhận trực tiếp:
Suy luận triển khai:
File/symbol thay đổi:
Test/evidence:
Kết quả:
Điểm chưa đạt / blocker:
Ảnh hưởng claim:
```

