# Khung bài M0

Khung này chỉ chứa cấu trúc và placeholder evidence. Nội dung học thuật phải do
nhóm tác giả viết và kiểm chứng. Không điền phần confirmatory trước khi có M1
freeze manifest và không chuyển số liệu dev thành claim test.

Các điều kiện để đổi placeholder thành nội dung:

1. Data card, split/root policy và `n_min` được duyệt tại M0.
2. FullTrain-A/B, LR/XGB, natural/balanced và UL/EC hoàn tất trên dev.
3. Resource calibration QĐ16 hoàn tất trên Kaggle T4.
4. Novelty ledger có truy vấn, ngày tra cứu và nguồn xác minh.
5. Candidate cuối được freeze tại M1 trước khi mở test.

## Evidence đã gắn vào bản ngày 21/10/2026

- Bảng headroom QĐ12 trong `main.tex` chỉ dùng development evidence.
- Archive bất biến:
  `../../results/cq_v1/skq_cq_v1_m0_headroom_2026_10_21.tar.gz`.
- Manifest và checksum gửi kèm nằm trong `evidence/`.
- Quyết định hiện hành là `rho*=0,5%` theo fallback đã đăng ký; bảng timing cũ
  ở 2% chỉ là evidence lịch sử và không đóng QĐ16.
- Trạng thái tổng thể vẫn là `PARTIAL`, chưa phải GO M0 và chưa được mở test.
