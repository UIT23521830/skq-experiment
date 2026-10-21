# Evidence QĐ16 partial gửi kèm báo cáo ngày 21/10/2026

## Provenance

- Archive: `../../../results/cq_v1/skq_cq_v1_m0_qd16_resource_rhostar.tar.gz`
- SHA-256: `83BEAA285714AB642B722DFDC9E816B38193833D9FB44F73E39E17218D04ECAA`
- Kích thước: `764.854` byte
- Commit thực nghiệm: `f29ad5b79a8a257f094177afa72b936f530bac56`
- Budget: `rho*=0,005`, đọc từ evidence QĐ12
- Phạm vi: train-only; test metric không được mở
- Pytest QĐ16: `17/17 PASS`

## Chín phương pháp đã hoàn tất

| Method | Upper time (s) | Upper RSS (GiB) | Decision |
|---|---:|---:|---|
| C01 uniform random | 0,002 | 1,303 | run direct |
| C02 stratified random | 0,021 | 1,287 | run direct |
| C03 phase-class random | 0,932 | 1,367 | run direct |
| CoreTab-XGB OVA adapted | 5.216,483 | 4,004 | run direct |
| BDIS native | 427,942 | 2,050 | run direct |
| GCoreSet benchmark | 2.128,576 | 1,876 | run direct |
| Moderate-DS adapted | 2,742 | 2,917 | run direct |
| CCS OOF-XGB adapted | 58,719 | 2,414 | run direct |
| Data-OOB official | 593,042 | 20,821 | run direct |

Mỗi phương pháp trên có đủ chín observation: ba replicate cho từng cỡ 50k,
200k và 800k. Các upper time đều dưới trần selector ba giờ. Data-OOB có footprint
RAM cao nhất và phải được giữ trong bảng tài nguyên.

## Phần chưa hoàn tất

- Kernel Thinning classwise: archive được đóng gói trước khi method này bắt đầu,
  nên không có checkpoint hợp lệ trong gói.
- Ba candidate `skq_pc`, `skq_pc_lrq_sq`, `skq_pc_r`: chưa chạy trong gói này.
- `resource_schedule_selector_only.json`: chưa sinh vì panel chưa đủ.
- Non-selector overhead cho lịch dev/test: chưa có.

Trạng thái trung thực là `PARTIAL 9/13`, không phải QĐ16 PASS. Cell resume phải
khôi phục archive theo checksum, bỏ qua chín method hoàn tất, ghi timeout/censored
riêng cho Kernel Thinning nếu vượt trần và tiếp tục ba candidate mà không gộp lỗi.
