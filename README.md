# SKQ Experiment — execution repository có gate kiểm toán

Project này hiện thực hóa ma trận thực nghiệm cho **Structured Kernel Quadrature
(SKQ)** trên dữ liệu bảng. Raw run trong repo này chỉ là execution artifact; chỉ
run qua gate, audit và export sang evidence store của paper mới được dùng làm số
liệu bài báo.

## 1. Câu hỏi nghiên cứu

Ta có tập train `D={(x_i,y_i)}` và budget `m=round(r×|D|)`. Mục tiêu là tạo một
tập train nhỏ hơn nhưng vẫn giữ:

1. utility trên nhiều downstream learner;
2. phân phối lớp và vùng cấu trúc quan trọng;
3. chi phí chọn, train, lưu trữ có lợi so với FullTrain;
4. khả năng tái lập bằng seed, commit và artifact bất biến.

Phương pháp đề xuất dùng `parent structure × class` để chia nhóm, cấp exact quota,
coarsen micro-strata theo class quota, biểu diễn RBF bằng Random Fourier Features
(RFF), chọn điểm bằng kernel herding và
tìm trọng số không âm tổng bằng khối lượng nhóm qua simplex-QP. P04/P05 ghép thêm
OOF query loss để bảo toàn vùng khó của một hoặc nhiều learner mà không dùng
dev/test.

Test không được dùng để chọn method hoặc siêu tham số. Config pilot hiện đánh giá
trên **dev**; kết quả đó chỉ phục vụ kiểm tra code và screening.

## 2. Panel đã được code

Config hiện hành
[`pilot_adult_full_seed11_v2.json`](configs/pilot_adult_full_seed11_v2.json) có
22 dòng, tương ứng 110 ô method × learner ở một seed và lên kế hoạch đủ 110 ô.
Control Stratified Random được mở cho đủ năm learner bằng override nằm trong
config/protocol hash. Config v1 được giữ lại để đọc đúng artifact cũ có bốn ô
`NA_CONTRACT`; thiếu dependency, vượt RAM hoặc vượt time gate vẫn được ghi
`BLOCKED/PREDICTED_OOM/PREDICTED_TIMEOUT`, không bị xóa khỏi mẫu số. Tên ngắn
`pilot_adult_seed11.json` là alias của full-v2.

| Nhóm | ID | Implementation và cách hiểu |
|---|---|---|
| Reference | `c00_full_train` | Train toàn bộ; không phải selector |
| Control | `c02_stratified_random` | Exact 5%; full-v2 chạy đủ LR/RF/XGB/CAT/MLP, confirmatory vẫn có thể khóa riêng |
| Native | `n01_coretab_dt_subset` | Gọi trực tiếp CoreTab-DT commit khóa; giữ native size |
| Native | `n02_coretab_xgb_subset` | Gọi trực tiếp CoreTab-XGB commit khóa; giữ native size |
| Native | `n_bdis_native` | Gọi BDIS upstream; bắt buộc `faiss`, không sklearn fallback |
| Native | `n_autocoreset_native` | Nhập artifact do driver environment riêng tạo |
| Adaptation | `a_craig_feature_space` | Facility-location/lazy-greedy feature-space; R1, không claim native |
| Official-source adapter | `n_gcoreset_benchmark` | Gọi trực tiếp `distill_coreset` từ benchmark Tabular Data Distillation; adapter chỉ seed và khôi phục index |
| Official-source adapter | `n_leverage_benchmark` | Gọi trực tiếp `distill_coreset_leverage_scores`; adapter inject import PCA/seed |
| Synthetic | `s_kip_tdbench` | Gọi KIP trong TDBench; lưu `generated_train.npz` |
| Synthetic | `s_mtt_tdbench` | Gọi trajectory matching trong TDBench |
| Synthetic | `s_gm_tdbench` | Gradient Matching (ICLR 2021) qua TDBench; patch gradient được khai báo |
| Synthetic | `s_datm_tdbench` | Difficulty-Aligned Trajectory Matching (ICLR 2024) qua TDBench; patch được khai báo |
| Synthetic | `s_tame_official` | Gọi `tame_synthesize` từ TAME; GPU/`max_rows` gate rõ ràng |
| Proposed | `p01_skq_coretab_dt` | SKQ dùng structure do N01 xuất |
| Proposed | `p02_skq_coretab_xgb` | SKQ dùng structure do N02 xuất |
| Proposed | `p03_skq_bdis_filtered` | SKQ trên candidate/structure BDIS; chỉ mở khi BDIS gate qua |
| Proposed | `p04_skq_lrq_sq` | P02 structure + OOF loss của LR |
| Proposed | `p05_skq_lrq_mq` | P02 structure + OOF loss LR/RF/XGB |
| Ablation | `d02_parent_structured_random` | Giữ structure/QP, thay herding bằng random trong nhóm |
| Ablation | `d04_global_rff_quadrature` | Bỏ parent structure, vẫn giữ class/RFF/herding/QP |
| Ablation | `d05_equal_group_weight` | Giữ index của P05, thay QP bằng trọng số đều trong nhóm |

GM và DATM là baseline deep chính thống về ý tưởng/paper nhưng lượt `full-v2`
dùng profile `pilot_resource_bounded`, không tự nhận là full-paper reproduction.
Artifact lưu toàn bộ tham số chạy và danh sách source patch. Cấu hình tham chiếu
đầy đủ của TDBench lớn hơn đáng kể và chỉ nên chạy ở stage scale riêng.

Không thêm baseline LLM vào ma trận số hiện tại. GReaT/LLM cần DataFrame thô với
tên cột, kiểu categorical và tokenizer/model checkpoint; runner hiện nhận
`X_train.npy` đã mã hóa. Ép LLM học các cột số ẩn danh sẽ sai cơ chế paper và phụ
thuộc tải model ngoài khi Kaggle Internet có thể bị tắt.

`p00_structured_kquad` là engine dùng chung, không phải dòng kết quả. Trong
`s1_screen`, P04/P05 được chạy trên **dev** với parent N02 đã khai báo trước và
artifact phải ghi `pre_freeze_dev_screen`, `confirmatory_eligible=false`. Đây chỉ
là sàng lọc thăm dò, không phải tuyên bố N02 đã thắng. Khi chạy ngoài vòng screen,
đặc biệt `s2_confirm` trên test, P04/P05 vẫn trả `GATE_LOCKED` nếu chưa có freeze
manifest hoặc parent không khớp winner đã freeze.

## 3. Native, benchmark, synthetic khác nhau thế nào

- **Native**: chạy implementation của tác giả đúng commit. Kích thước thực tế
  được giữ nguyên; không trim/pad để giả thành 5%.
- **Official-source adapter**: chạy trực tiếp function của repo tác giả đã khóa
  commit; adapter chỉ chuyển input/output và vá boundary import/seed/index.
- **Synthetic**: sinh X/y mới nên không có `selected_indices.npy`; nó dùng contract
  và storage-matched table riêng.
- **Proposed/ablation**: code trong package này, classwise coarsening, exact-budget,
  mass-preserving weights và invariant tests.

AutoCoreset cần boundary riêng vì upstream phụ thuộc API cũ. BDIS cần Faiss. KIP
cần JAX/neural-tangents; MTT/GM/DATM cần PyTorch. Nếu môi trường không đạt,
ledger nói rõ lý do và tuyệt đối không chạy một thuật toán khác dưới cùng tên.

CoreTab upstream ở commit khóa chỉ có native subset contract cho nhãn nhị phân.
Với dataset đa lớp, N01/N02 được ghi `NA_CONTRACT`; adapter chỉ xuất leaf structure
đa lớp cho P01/P02 và ghi rõ `structure_only=true`, không tạo điểm native CoreTab
giả bằng một OVA tùy ý.

## 4. Cấu trúc project

```text
skq_experiment/
├── configs/                         # protocol/stage, không chứa thuật toán
├── data/raw/                        # raw data, Git ignore
├── data/processed/                  # split + train-only preprocessing, Git ignore
├── external/
│   ├── official_repos.lock.json     # URL + commit khóa
│   └── repos/                       # checkout repo tác giả, Git ignore
├── artifacts/                       # selection, prediction, metric, ledger
├── requirements/                    # base, Kaggle và native-isolated
├── scripts/                         # fetch repo, driver AutoCoreset, Kaggle entry
├── src/skq_exp/
│   ├── data/                        # download, split, preprocessing và manifest
│   ├── methods/
│   │   ├── native/                  # boundary repo tác giả
│   │   ├── benchmark/               # reproduction benchmark có khai báo
│   │   ├── synthetic/               # contract KIP/MTT/GM/DATM/TAME sinh X/y
│   │   └── proposed/                # RFF, allocation, herding, QP, query loss
│   ├── training/                    # 5 learner, weight contract và metrics
│   ├── experiments/                 # DAG, gate, runner và failure ledger
│   └── reports/                     # bảng long, trạng thái và break-even
└── tests/                            # contract/unit/end-to-end tests
```

Mỗi file Python có phần ghi chú đầu file bằng tiếng Việt, mô tả đầu vào, việc nó
làm và lý do tồn tại. Thuật toán không được viết trong notebook hoặc shell cell.

## 5. Cài và kiểm tra

PowerShell:

```powershell
cd C:\source\paper\skq_experiment
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[kaggle-full,data,dev]"
python scripts\fetch_official_repos.py
pytest -q
skq doctor
skq smoke --config configs\s0_smoke.json
```

`fetch_official_repos.py` kiểm tra đúng bảy commit trong lock file. Không commit
các checkout này lên GitHub.

## 6. Chạy Adult một seed

Tải và chuẩn bị dữ liệu:

```powershell
skq fetch-data --config configs\pilot_adult_full_seed11_v2.json --dataset adult_uci2_v1
skq prepare --config configs\pilot_adult_full_seed11_v2.json --dataset adult_uci2_v1
```

Kiểm tra nhanh trước (FullTrain-LR + D04-LR):

```powershell
skq run --config configs\pilot_adult_quick_seed11.json `
  --selector-seed 11 --max-ram-gb 8 --timeout-seconds 1800 --max-threads 4
```

Chạy toàn bộ candidate matrix trên Adult, seed 11:

```powershell
skq plan --config configs\pilot_adult_full_seed11_v2.json
skq run --config configs\pilot_adult_full_seed11_v2.json `
  --selector-seed 11 --model-seed 42 `
  --max-ram-gb 8 --timeout-seconds 3600 --max-threads 4 `
  --max-estimated-operations 30000000000
```

Đây mới là lệnh **full-v2**. Nó đi qua cả 22 method và 5 learner; không phải lệnh
2-method quick check. `skq plan` phải báo 21 phương pháp nén/sinh, 110 ô tổng và
110 ô được lên kế hoạch chạy. P04/P05 chạy ở dev dưới nhãn pre-freeze; chỉ
confirmatory/test mới giữ `GATE_LOCKED` cho tới khi base winner đã freeze.
Dependency bị thiếu không được coi là kết quả cuối. Chạy riêng
một ô để debug:

```powershell
skq run --config configs\pilot_adult_full_seed11_v2.json `
  --method p02_skq_coretab_xgb --learner lr --selector-seed 11
```

Các method phụ thuộc structure phải chạy source trước nếu chạy riêng: N01 trước
P01; N02 trước P02/P04/P05/D02; BDIS trước P03. Full config đã sắp đúng thứ tự và
structure artifact cũng có thể được nạp lại từ ổ đĩa.

Sau khi seed 11 ổn, thêm seed mà không sửa code:

```powershell
skq run --config configs\pilot_adult_full_seed11_v2.json `
  --selector-seed 11 --selector-seed 29 --selector-seed 47
```

## 7. Điều gì được lưu và có nặng máy không

Mặc định `save_models=false`. Một run chọn dòng lưu:

```text
manifest.json
selected_indices.npy
sample_weights.npy
diagnostics.json
timings.json
predictions.npz
metrics_overall.json
metrics_per_label.csv
metrics_all.json
confusion_matrix.csv
cost.json
```

Synthetic thay hai file selection bằng `generated_train.npz`. C00 chỉ lưu
full-reference manifest, không tạo `selected_indices.npy` giả. Model chỉ được lưu
khi thêm `--save-model`; đây mới là loại artifact dễ phình lớn. Prediction được
nén và Adult nhỏ, nên phần mặc định chủ yếu là metric/index chứ không phải hàng
chục checkpoint.

Guard bảo vệ máy gồm:

- preflight RAM và số phép tính;
- hard resource check giữa các batch/vòng của SKQ và Gonzalez;
- CRAIG tính cả ma trận pairwise O(n²) trong dự báo RAM;
- KIP tính cả kernel target-support, gradient và optimizer trong dự báo RAM;
- KIP/MTT/GM/DATM không có trần budget tùy ý; OOM/timeout thật được ghi tách biệt;
- Trên Kaggle, `scripts/run_kaggle_split_env.py` chạy panel trước, sau đó
  pin đồng bộ JAX/CUDA 0.4.38 và chạy riêng KIP trong process mới; hai
  pha vẫn dùng cùng protocol hash và được đóng gói chung;
- trạng thái dừng được ghi vào manifest/ledger.

Repo ngoài không phải method nào cũng có điểm kiểm tra giữa vòng; với chúng,
preflight là lớp bảo vệ chính. Requested size và realized size đều được lưu để
không đánh đồng giới hạn khả thi của source với lỗi tài nguyên.

## 8. Metrics

Mỗi prediction tạo hơn 25 metric tổng thể: accuracy, balanced accuracy,
precision/recall/F1/Jaccard macro-micro-weighted, MCC, Cohen kappa, quadratic
kappa, worst-class F1/recall, ROC-AUC và PR-AUC macro/weighted, log-loss, Brier và
ECE-15. Mỗi label có support, prevalence, TP/FP/TN/FN, precision, recall,
specificity, NPV, F1/F2, FPR/FNR, MCC, kappa, ROC-AUC và PR-AUC.

`cost.json` tách selection/generation, RFF/herding/QP, fit, predict, total, CPU,
RSS lower bound, VRAM, I/O, throughput, compression ratio và storage artifact.
`skq aggregate` ghép FullTrain để tính break-even reuse khi fit coreset thực sự
nhanh hơn FullTrain.

```powershell
skq aggregate --artifact-root artifacts
```

Đầu ra chính:

- `artifacts/aggregate/runs_long.csv`;
- `artifacts/aggregate/status_summary.csv`;
- `artifacts/<experiment_id>/run_ledger.json`.

## 9. Trạng thái kết quả pilot cũ

Archive Adult seed 11 trước commit sửa contract chỉ là
`integration_debug_adult_seed11`. Các run P01/P02/P04/P05 cũ đã bị vô hiệu hóa vì
allocation trước đây bỏ mass của zero-quota strata. Phải chạy lại bằng schema v3;
không được dùng các metric cũ để chọn winner hoặc viết bảng.

Structure schema v3 bắt buộc có `row_ids`, `stratum_ids`, `candidate_mask` cùng
dataset/split fingerprint. Artifact schema cũ bị từ chối khi replay.

## 10. Quy tắc trước khi viết bảng bài báo

1. Chọn representative/base winner chỉ bằng dev trên đủ dataset/seeds.
2. Freeze method, hyperparameter, query portfolio, contrasts và config hash.
3. Chỉ sau đó tạo `artifacts/freeze/freeze_manifest.json` và mở `s2_confirm`.
4. Confirmatory chính: budget 5%, XGBoost, Macro-F1, MCC, worst-class và Holm.
5. Transfer: LR/RF/XGB/CatBoost/MLP với cùng selection artifact.
6. Native-size và exact-5% phải nằm ở cột/figure khác nhau.
7. Synthetic báo cả row-count-matched và storage-matched.
8. Failure/OOM/timeout/NA phải ở lại bảng.

Trong pilot, MLP chạy số epoch cố định và không dùng dev để early-stop. Khi bổ
sung tuning chính thức, inner-validation phải được tách từ train trước selector,
freeze hyperparameter trên FullTrain rồi dùng lại cho mọi method.

Hướng dẫn đưa code lên GitHub và chạy Kaggle nằm trong
[`GUIDELINE_GITHUB_KAGGLE.md`](GUIDELINE_GITHUB_KAGGLE.md).

## 11. Nguồn quyết định khoa học

- `C:\source\paper\lý thuyết\GOI_THUC_NGHIEM_NEN_V1\docs\19_MASTER_RESEARCH_AND_IMPLEMENTATION_SPEC.md`
- `C:\source\paper\lý thuyết\nhận xét\implementation_plan.md`
- `C:\source\paper\outputs\experiment_matrix_20261006\MA_TRAN_THUC_NGHIEM_SKQ_FULL.xlsx`

Nếu code và protocol đã freeze mâu thuẫn, dừng run và ghi deviation; không sửa
thiết lập sau khi nhìn test.
