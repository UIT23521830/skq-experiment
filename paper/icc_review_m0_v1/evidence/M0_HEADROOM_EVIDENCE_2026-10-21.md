# Evidence headroom QĐ12 gửi kèm báo cáo ngày 21/10/2026

## Nguồn và tính toàn vẹn

- Archive: `../../../results/cq_v1/skq_cq_v1_m0_headroom_2026_10_21.tar.gz`
- SHA-256: `2839B7D1AF1284999DD1AC1ED406058A9D875E7048A5FB77E2C82AD3EE4EE4A3`
- Kích thước: `15.588.442` byte
- Commit thực nghiệm: `9b07f6f769d8504a2555bf6608411c8f5131f8be`
- Phạm vi: development-only; `test_metrics_opened=false`
- Learner: XGBoost; class-weight policy: natural provisional
- Dữ liệu đầu vào của quyết định: FullTrain-B và C02
- Selector seeds: `11, 29, 47`
- Cách gom phase: trung bình P1--P4 bên trong từng seed
- Completeness: `52/52` evaluation thành công; `54/54` pytest đạt

## Kết quả quyết định

| rho | UL C02 trung bình | FullTrain-B trừ C02 | eligible |
|---:|---:|---:|:---:|
| 0,005 | 0,6501527262 | 0,0041850892 | false |
| 0,01 | 0,6551794667 | -0,0008416513 | false |
| 0,02 | 0,6472826063 | 0,0070552091 | false |
| 0,05 | 0,6520009739 | 0,0023368415 | false |

FullTrain-B UL là `0,6543378154`; gap đăng ký là `0,01`. Không mức nào đạt
ngưỡng, nên fallback đã đăng ký chọn mức nhỏ nhất: `rho*=0,005` (0,5%).

## Giới hạn diễn giải

Đây là quyết định giao thức trên dev, không phải kết quả confirmatory và không
chứng minh 0,5% tốt hơn mọi ngân sách lớn hơn. Archive không cho phép ghi GO M0
một mình. QĐ16 vẫn phải đo 10 selector cố định và ba candidate tại rho mới chốt;
FullTrain-A, LR tuning, group-unit confirmation và raw checks còn mở. Không mở
test trước freeze M1.

## File máy đọc

- `headroom_decision_2026_10_21.json`: bản tự chứa của quyết định QĐ12.
- `M0_EVIDENCE_MANIFEST_2026-10-21.json`: provenance, completeness và trạng thái.
- `SHA256SUMS.txt`: checksum của archive nguồn và quyết định JSON canonical.
