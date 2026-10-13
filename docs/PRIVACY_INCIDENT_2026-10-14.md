# Privacy deviation 2026-10-14

## Phạm vi xác nhận

Audit `scanner_version=1.0.0` tại commit nền `025e5ea` phát hiện workbook
`MA_TRAN_THUC_NGHIEM_SKQ_FULL.xlsx` đang được Git theo dõi và có ba object mang
cùng path trong lịch sử. Đây là kiểu file nhị phân không thuộc public allowlist.

Finding này **không tự chứng minh** workbook chứa dữ liệu dòng CQ, thông tin sinh
viên hay credential. Nó được ghi là vi phạm chính sách phát hành vì nội dung nhị
phân không thể review bằng diff và không nên nằm trong code repository.

## Hành động đã thực hiện

- Bỏ workbook khỏi Git index; file local vẫn được giữ nguyên và đã có rule ignore.
- Repo đã được nhóm chuyển sang private trước lần audit này (xác nhận của nhóm;
  script không tự kiểm được cài đặt GitHub).
- Không rewrite lịch sử, không force-push và không xóa object âm thầm.
- G01 vẫn **chưa đạt** vì history finding còn tồn tại.

## Hành động cần phê duyệt trước public release

Chọn một trong hai phương án và ghi người duyệt:

1. Tạo repo public sạch từ allowlist tại một commit/tag được phê duyệt; repo hiện
   tại tiếp tục private để giữ lịch sử kiểm toán.
2. Rewrite lịch sử repo hiện tại rồi force-push, chỉ khi giảng viên/nhóm duyệt rõ
   vì thao tác này làm thay đổi commit/tag đã chia sẻ.

Cho đến khi có quyết định, không đánh dấu privacy gate là pass và không phát hành
archive public. Nếu cần công bố ma trận, xuất một bản Markdown/CSV đã kiểm tra,
không chứa dữ liệu mức dòng và có checksum riêng.
