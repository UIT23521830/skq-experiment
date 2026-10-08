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
        gọi TDBench, lưu generated_train.npz
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
| BDIS | hoàn tất | `faiss-cpu`; nếu thiếu trả BLOCKED |
| AutoCoreset | boundary + driver hoàn tất | environment riêng tạo artifact đúng fingerprint |
| CRAIG feature-space | adaptation R1 | pairwise preflight không vượt RAM/ops; không claim native |
| Gonzalez, Leverage | hoàn tất và đã smoke Adult | sklearn |
| KIP-TDBench | adapter output riêng hoàn tất | JAX + neural-tangents và max_rows gate |
| MTT-TDBench | adapter output riêng hoàn tất | PyTorch và max_rows gate |
| P01, P02 | hoàn tất và đã smoke Adult | N01/N02 structure |
| P03 | hoàn tất theo candidate-mask contract | BDIS phải qua gate và pool đủ budget |
| P04, P05 | code + gate hoàn tất | frozen base winner + OOF query portfolio; thiếu freeze trả GATE_LOCKED |
| D02, D04, D05 | hoàn tất | D02 cần parent; D05 cần source selection cùng run |

## Không được tuyên bố quá mức

- Pilot một seed trên dev chỉ là integration evidence.
- P04/P05 không chạy chỉ vì config pilot có N02; freeze phải xác nhận đúng base source.
- Native CoreTab chạy ở realized size, không phải exact 5%.
- Gonzalez/Leverage là benchmark reproduction, không gọi native paper.
- BDIS/AutoCoreset/KIP/MTT chỉ vào bảng utility khi gate thật sự SUCCESS.
- `a_craig_feature_space` là adaptation, không nằm dưới nhãn native CRAIG.
- Failure là một kết quả về khả năng tái hiện/chi phí, không được đổi method rồi giữ tên.
