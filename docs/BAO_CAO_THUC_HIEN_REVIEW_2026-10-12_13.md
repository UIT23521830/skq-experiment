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

### 14/10/2026 — Chuẩn hóa trọng số và tách operation khỏi gate

**Xác nhận trực tiếp đã áp dụng**

- Effective sample weight của FullTrain, subset thật và synthetic được chuẩn hóa
  mean bằng 1 sau khi nhân method weight với class weight.
- Số phép tính ước lượng chỉ còn là diagnostic; vượt ngưỡng cũ không tạo
  `predicted_timeout`.
- `predicted_oom`, `oom` và `timeout` vẫn là ba trạng thái riêng: RAM dự báo vẫn
  có thể chặn trước, còn RSS/thời gian thật được ResourceGuard kiểm tra khi chạy.

**Suy luận triển khai**

- Giữ khóa `max_estimated_operations` cũ để đọc được config lịch sử, nhưng đổi
  tên ý nghĩa trong evidence thành `legacy_reference_operations` và ghi rõ
  `decision_role=diagnostic_only`. Việc này tương thích ngược, không biến ngưỡng
  cũ thành tiêu chí loại mẫu.
- Chỉ ghi thống kê count/min/max/mean/sum/zero_count của weight vào cost artifact,
  không nhân bản cả vector trọng số trong bảng metric.

**Bằng chứng cục bộ**

- `tests/test_weights.py`: kiểm tra mean=1 và bất biến với phép nhân toàn cục.
- `tests/test_resources.py`: kiểm tra operation vượt mốc cũ vẫn được phép chạy.
- `tests/test_temporal_evaluation.py`: kiểm tra weight thực sự truyền vào learner
  và metadata cost đều có mean=1.

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

