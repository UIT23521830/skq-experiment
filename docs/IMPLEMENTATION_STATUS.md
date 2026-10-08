# Full candidate matrix — trạng thái implementation

Tài liệu này là bản kiểm tra nhanh cho team code. `implemented` nghĩa là có đường
code thật và contract artifact; nó không đảm bảo mọi máy đều đủ dependency/RAM.

## Pseudocode của một full run

```text
load processed train/dev; giữ test khóa
for method theo thứ tự config:
    preflight RAM / operations / synthetic-size
    if native structure producer:
        gọi repo đúng commit
        lưu native selection và structure.npz
    elif synthetic:
        gọi repo synthetic đã khóa, lưu generated_train.npz
    elif proposed:
        nạp parent structure đã sinh
        nếu P04/P05: tạo OOF query loss chỉ từ train
        class quota → deterministic coarsening → exact group quota
        → RFF → exact squared-distance herding → simplex-QP
    elif D05:
        giữ index của source method, tính lại weight đều theo nhóm
    for learner hợp contract:
        train với class weight(full train) × sample weight(method)
        predict dev
        lưu overall/per-label/probability/cost metrics
    ghi cả success lẫn failure vào ledger
aggregate; chỉ sau dev freeze mới được mở test
```

## Trạng thái theo boundary

| ID | Code | Điều kiện để có SUCCESS |
|---|---|---|
| C00, C02 | hoàn tất | sklearn/XGBoost |
| N01, N02 | hoàn tất và đã smoke Adult | Native subset cần binary target; đa lớp chỉ xuất structure và ghi NA |
| BDIS | hoàn tất | `faiss-cpu>=1.10` hỗ trợ Python 3.13; nếu thiếu trả BLOCKED |
| AutoCoreset | boundary + driver hoàn tất | environment riêng có `iterative-stratification`, tạo artifact đúng fingerprint |
| CRAIG feature-space | adaptation R1 | pairwise preflight không vượt RAM/ops; không claim native |
| Gonzalez, Leverage | hoàn tất và đã smoke Adult | Gọi trực tiếp hai function upstream; adapter vá seed/index/PCA |
| KIP-TDBench | adapter output riêng hoàn tất | JAX + neural-tangents; vá import `jax.config` đã bị loại bỏ, không đổi phép tính KIP; budget được hạ về mức source `10*N` không hoàn lại khả thi và lưu requested/realized |
| MTT-TDBench | adapter có vá lỗi source và kiểm tra no-op | PyTorch; bật gradient, clone snapshot expert và dùng seed/RNG đúng cơ chế MTT chính thức; từ chối `success` nếu toàn bộ output vẫn là dòng train gốc |
| TAME official | adapter output riêng hoàn tất | PyTorch/GPU tùy chọn và max_rows gate |
| P01, P02 | hoàn tất và đã smoke Adult | N01/N02 structure |
| P03 | hoàn tất theo candidate-mask contract | BDIS phải qua gate và pool đủ budget |
| P04, P05 | code + gate hoàn tất | s1 screen trên dev với parent khai báo trước và nhãn pre-freeze; confirmatory/test bắt buộc frozen base winner |
| D02, D04, D05 | hoàn tất | D02 cần parent; D05 cần source selection cùng run |

## Không được tuyên bố quá mức

- Pilot một seed trên dev chỉ là integration evidence.
- P04/P05 ở pilot chỉ là dev screen, không được ghi là confirmatory; freeze vẫn phải xác nhận đúng base source trước khi mở test.
- Native CoreTab chạy ở realized size, không phải exact 5%.
- Gonzalez/Leverage chạy trực tiếp function từ benchmark repo đã khóa; vẫn ghi là
  official-source adapter vì output contract của upstream không trùng contract
  index/weight của SKQ.
- TDColER/TDBench là pipeline hai giai đoạn (learn encoder/decoder rồi distill),
  chưa được gắn vào full runner như một hàm synthetic đơn lẻ; không ghi giả là
  đã chạy TDColER chỉ vì repo TDBench đã được fetch.
- BDIS/AutoCoreset/KIP/MTT chỉ vào bảng utility khi gate thật sự SUCCESS.
- `a_craig_feature_space` là adaptation, không nằm dưới nhãn native CRAIG.
- Failure là một kết quả về khả năng tái hiện/chi phí, không được đổi method rồi giữ tên.
