# Baseline deep bổ sung trong protocol full-v2

Tài liệu này khóa cách gọi tên và mức độ tái hiện để bảng kết quả không vô tình
ghi các adapter là implementation nguyên trạng của paper.

## Gradient Matching

- ID: `s_gm_tdbench`.
- Paper: *Dataset Condensation with Gradient Matching*, ICLR 2021 (Oral).
- Paper chính thức: <https://openreview.net/forum?id=mSAKhLYLSsl>.
- Source paper: <https://github.com/VICO-UoE/DatasetCondensation>.
- Source thực thi trong project: hàm `gradient_matching` của TDBench tại commit
  đã khóa `0b3ee85065c5b51372e59c31c699fd637a13a357`.
- Trạng thái: `benchmark-source adapter with declared patch`, không phải source
  paper nguyên trạng. Patch `gm_trainable_synthetic_data` bật gradient cho
  synthetic features; nếu không có patch, optimizer dữ liệu không cập nhật.
- Đầu ra: dữ liệu train tổng hợp, budget chia đều theo lớp; downstream vẫn dùng
  cùng LR/RF/XGB/CatBoost/MLP và cùng dev split như các dòng khác.

BibTeX:

```bibtex
@inproceedings{zhao2021dataset,
  title={Dataset Condensation with Gradient Matching},
  author={Zhao, Bo and Mopuri, Konda Reddy and Bilen, Hakan},
  booktitle={International Conference on Learning Representations},
  year={2021},
  url={https://openreview.net/forum?id=mSAKhLYLSsl}
}
```

## Difficulty-Aligned Trajectory Matching

- ID: `s_datm_tdbench`.
- Paper: *Towards Lossless Dataset Distillation via Difficulty-Aligned
  Trajectory Matching*, ICLR 2024.
- Paper chính thức: <https://openreview.net/forum?id=rTBL8OhdhH>.
- Source paper: <https://github.com/NUS-HPC-AI-Lab/DATM>.
- Source thực thi trong project: hàm `datm` của TDBench tại cùng commit khóa.
- Trạng thái: `benchmark-source adapter with declared patches`. Bảy patch có ID
  `datm_*` sửa seed expert, snapshot alias, gradient của synthetic data/learning
  rate và RNG trajectory. Artifact luôn lưu đủ danh sách patch.
- Đầu ra: dữ liệu train tổng hợp, budget chia đều theo lớp.

BibTeX:

```bibtex
@inproceedings{guo2024towards,
  title={Towards Lossless Dataset Distillation via Difficulty-Aligned Trajectory Matching},
  author={Guo, Ziyao and Wang, Kai and Cazenavette, George and Li, Hui and Zhang, Kaipeng and You, Yang},
  booktitle={International Conference on Learning Representations},
  year={2024},
  url={https://openreview.net/forum?id=rTBL8OhdhH}
}
```

## Vì sao chưa thêm LLM/GReaT

GReaT là paper có thật tại ICLR 2023 và có source công khai:
<https://openreview.net/forum?id=cEygmQNOeI> và
<https://github.com/tabularis-ai/be_great>. Tuy nhiên cơ chế của nó cần dữ liệu
bảng thô có tên cột/kiểu dữ liệu để tuần tự hóa thành văn bản. Contract hiện tại
chỉ đưa ma trận số đã tiền xử lý vào generator. Thêm GReaT ở boundary này sẽ
không còn đúng paper, đồng thời buộc Kaggle tải model Hugging Face bên ngoài.
Vì vậy full-v2 chưa đưa LLM vào mẫu số; chỉ bổ sung khi project có raw-tabular
generator contract, checkpoint lock và cache offline riêng.

## Mức chạy

Config `pilot_adult_full_seed11_v2.json` dùng profile
`pilot_resource_bounded`. Đây là screening/integration run, không phải tuyên bố
tái hiện toàn bộ hyperparameter của paper. `configured_parameters`, commit,
patch, requested rows và realized rows đều được ghi trong artifact để có thể
nâng lên full profile sau khi pilot qua gate.
