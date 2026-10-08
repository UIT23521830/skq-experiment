# Hướng dẫn GitHub → Kaggle

Tài liệu này hướng dẫn người chưa có ngữ cảnh đưa project lên GitHub, gắn dữ liệu
trên Kaggle và chạy đúng thứ tự. Dữ liệu raw và artifact lớn luôn nằm ngoài Git;
GitHub chỉ lưu code, config, test và các manifest nhỏ.

## 1. Chuẩn bị trước khi đưa lên GitHub

Từ thư mục project:

```powershell
cd C:\source\paper\skq_experiment
python -m pip install -e ".[kaggle-full,data,dev]"
python scripts\fetch_official_repos.py
pytest
skq doctor
```

Chỉ tiếp tục khi test đều đạt. Kiểm tra `git status` và bảo đảm không có file dữ
liệu, model hoặc predictions. `.gitignore` đã chặn các thư mục lớn, nhưng người
đẩy code vẫn phải đọc danh sách thay đổi trước khi commit.

## 2. Tạo GitHub repository

```powershell
git init
git add .
git status
git commit -m "Initialize reproducible SKQ experiment"
git branch -M main
git remote add origin https://github.com/<tai-khoan>/<ten-repo>.git
git push -u origin main
```

Thay `<tai-khoan>` và `<ten-repo>` bằng repository thật. Không lưu Kaggle token,
API key hoặc đường dẫn cá nhân trong code/config.

## 3. Dữ liệu nào cần có trên Kaggle

Tạo một hoặc nhiều Kaggle Dataset riêng tư, giữ nguyên các thư mục con sau:

```text
skq-public-data/
├── adult_uci2_v1/
├── creditcard_ulb2013_v1/
├── letter_uci59_v1/
├── covertype_uci31_v1/
├── jannis_openml41168_v1/
└── helena_openml41169_v1/
```

Nguồn cần tải:

- Adult: `https://archive.ics.uci.edu/dataset/2/adult`.
- Letter: `https://archive.ics.uci.edu/dataset/59/letter+recognition`.
- Covertype: `https://archive.ics.uci.edu/dataset/31/covertype`.
- Credit Card: Kaggle dataset `mlg-ulb/creditcardfraud`.
- Jannis: OpenML data ID `41168`.
- Helena: OpenML data ID `41169`.

Không gộp MOOCCubeX vào public-static dataset. MOOCCubeX cần Kaggle Dataset riêng
vì có manifest, feature và temporal split riêng.

## 4. Tạo Kaggle Notebook

1. Chọn **New Notebook**.
2. Bật Internet chỉ khi cần clone GitHub hoặc cài dependency.
3. Gắn Kaggle Dataset chứa public data bằng **Add Input**.
4. Chọn GPU chỉ cho MLP hoặc synthetic generation; selector và ML tabular có thể
   chạy CPU.
5. Bật lưu output vì artifact cần tải về sau mỗi stage.

Cell đầu tiên:

```bash
!git clone https://github.com/<tai-khoan>/<ten-repo>.git /kaggle/working/skq_experiment
%cd /kaggle/working/skq_experiment
!python -m pip install -q -e ".[kaggle-full]"
!python scripts/fetch_official_repos.py
!skq doctor
```

`kaggle-full` cài cả BDIS (`faiss-cpu`), AutoCoreset
(`iterative-stratification`) và KIP-TDBench (`jax==0.4.38`,
`neural-tangents==0.6.5`). Pin JAX này giữ API mà source TDBench khóa commit đang
dùng và có wheel Python 3.13. Nếu `skq doctor` vẫn báo thiếu một trong các gói này,
run tương ứng phải được xem là `BLOCKED`, không phải kết quả utility.

Nếu Internet bị tắt, upload source dưới dạng Kaggle Dataset hoặc Notebook input,
sau đó copy vào `/kaggle/working/skq_experiment`. Không sửa code trực tiếp trong
cell vì thay đổi đó khó truy vết bằng commit.

## 5. Khai báo đường dẫn Kaggle

Trong config chạy, dùng:

```json
{
  "paths": {
    "raw_root": "/kaggle/input/skq-public-data",
    "processed_root": "/kaggle/working/skq_data/processed",
    "artifact_root": "/kaggle/working/skq_artifacts",
    "external_root": "/kaggle/working/skq_experiment/external/repos"
  }
}
```

`/kaggle/input` chỉ đọc; mọi file tạm, processed data và artifact phải ghi vào
`/kaggle/working`.

## 6. Thứ tự lệnh trên Kaggle

```bash
# 1. Kiểm tra môi trường và test nhanh
!pytest -q
!skq smoke --config configs/s0_smoke.json

# 2. Tải/chuẩn bị Adult và kiểm tra manifest
!skq fetch-data --dataset adult_uci2_v1 --config configs/pilot_adult_full_seed11.json
!skq prepare --dataset adult_uci2_v1 --config configs/pilot_adult_full_seed11.json

# 3. Quick check rồi candidate matrix; LRQ được screen trên dev với parent khai báo trước
!skq run --config configs/pilot_adult_quick_seed11.json --selector-seed 11
!skq run --config configs/pilot_adult_full_seed11.json --selector-seed 11 \
  --max-ram-gb 12 --timeout-seconds 7200 --max-threads 4

# 4. Sau dev screen, tạo freeze_manifest schema v3 theo docs/freeze_manifest.example.json.
#    Chỉ sau đó kết quả P04/P05 mới được phép đi vào confirmatory/test.
!skq run --config configs/s2_confirm.json --dataset adult_uci2_v1

# 5. Gom kết quả của những run đã hoàn thành
!skq aggregate --artifact-root /kaggle/working/skq_artifacts
```

Runner hiện ghi đè đúng run directory khi cùng run ID và gộp ledger theo run ID,
nhưng chưa có scheduler tự bỏ qua mọi run thành công. Vì vậy nên chạy theo method
hoặc checkpoint sau từng nhóm trên Kaggle; không giả định lệnh bị ngắt sẽ tự resume
từ đúng vòng lặp bên trong selector.

Trong lần chạy đầu, luôn thêm `--selector-seed 11`. Sau khi artifact và metric đã
được kiểm tra, có thể chạy nhiều seed bằng cách lặp option:

```bash
!skq run --config configs/pilot_adult_full_seed11.json --dataset adult_uci2_v1 \
  --selector-seed 11 --selector-seed 29 --selector-seed 47
```

Trên máy có RAM hạn chế, đặt guard ngay trong lệnh:

```bash
!skq run --config configs/pilot_adult_full_seed11.json --dataset adult_uci2_v1 \
  --selector-seed 11 --max-ram-gb 12 --timeout-seconds 7200 \
  --max-estimated-operations 50000000000
```

Mặc định không lưu fitted model; selection, prediction nén, metric, cost và manifest
vẫn được giữ. Chỉ thêm `--save-model` cho run cần checkpoint.

## 7. Checkpoint để tránh mất kết quả

Sau mỗi dataset hoặc selector seed, nén artifact:

```bash
!tar -czf /kaggle/working/skq_checkpoint.tar.gz -C /kaggle/working skq_artifacts
```

Chọn **Save Version** để Kaggle giữ file trong Output. Khi chạy notebook mới, gắn
output của version trước làm input rồi giải nén sang `/kaggle/working`.

## 8. Repo đối chứng

Các repo tác giả được khóa commit trong `external/official_repos.lock.json`.
CoreTab và BDIS có adapter native trực tiếp; CRAIG feature-space là adaptation R1.
AutoCoreset dùng driver environment
riêng; KIP/MTT giữ dependency nặng của TDBench. Output đều mang commit/provenance.

Quy trình:

1. Chạy `python scripts/fetch_official_repos.py` để clone/kiểm commit.
2. Lưu `pip freeze`, lệnh chạy và patch nếu có.
3. Chạy native smoke trên dataset anchor.
4. Kiểm tra row identity và output type.
5. AutoCoreset chạy `python scripts/run_autocoreset_native.py --config ... --dataset ... --seed 11`; chỉ artifact qua gate mới được runner nhập.

KIP cần JAX và neural-tangents, MTT cần PyTorch. Với 5% Adult, config mặc định
chặn synthetic nếu vượt 500 dòng; đây là resource gate, không phải lỗi mất method.
Chỉ nâng `method_options.<method>.max_rows` sau khi smoke trên GPU thành công.

## 9. Tải kết quả về máy

Từ trang Output của Kaggle tải:

- `skq_checkpoint.tar.gz`;
- bảng tổng hợp CSV/JSON;
- log lỗi/OOM/timeout;
- freeze manifest;
- hình và bảng dùng cho bài báo.

Giải nén vào một thư mục artifact riêng, không ghi đè dữ liệu local chưa kiểm
tra. Sau đó chạy `skq aggregate` để tái tạo leaderboard và kiểm tra run IDs.

## 10. Những lỗi cần tránh

- Không upload raw data hoặc token lên GitHub.
- Không dùng test để chọn base winner.
- Không chạy FullTrain lặp lại theo selector seed.
- Không ép native method về exact 5% bằng trim/pad.
- Không đổi method khi OOM rồi giữ nguyên tên trong bảng.
- Không ghi metric không xác định thành 0.
- Không chỉnh portfolio query, kernel hoặc budget sau khi đã xem test.
