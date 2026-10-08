"""File này đọc raw data, tạo split ổn định và fit preprocessing trên train.

Sau khi chạy, mỗi dataset có các mảng NPY cùng manifest về schema, row ID và hash.
Selector chỉ đọc `X_train/y_train`; dev/test được runner giữ ở bước đánh giá.
"""

from __future__ import annotations

import json
import shutil
import urllib.request
import zipfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.datasets import fetch_openml
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, OneHotEncoder, StandardScaler

from ..artifacts import atomic_json, sha256_file
from .registry import DatasetSpec, get_dataset_spec


SPLIT_SEED = 20_261_002


def fetch_dataset(dataset_id: str, raw_root: str | Path, *, overwrite: bool = False) -> Path:
    """Tải raw public data đã đăng ký; hiện tự động hóa Adult trước cho pilot."""
    get_dataset_spec(dataset_id)
    output = Path(raw_root) / dataset_id
    if dataset_id != "adult_uci2_v1":
        raise RuntimeError(
            f"{dataset_id} chưa có downloader tự động; xem README để tải từ nguồn chính thức"
        )
    expected = [output / "adult.data", output / "adult.test", output / "adult.names"]
    if all(path.exists() for path in expected) and not overwrite:
        return output
    output.mkdir(parents=True, exist_ok=True)
    archive = output / "adult.zip"
    url = "https://archive.ics.uci.edu/static/public/2/adult.zip"
    with urllib.request.urlopen(url, timeout=120) as response, archive.open("wb") as stream:
        shutil.copyfileobj(response, stream)
    with zipfile.ZipFile(archive) as zipped:
        safe_members = [name for name in zipped.namelist() if Path(name).name in {"adult.data", "adult.test", "adult.names"}]
        if len(safe_members) < 3:
            raise RuntimeError("Archive Adult thiếu file chuẩn")
        for member in safe_members:
            target = output / Path(member).name
            with zipped.open(member) as source, target.open("wb") as destination:
                shutil.copyfileobj(source, destination)
    archive.unlink(missing_ok=True)
    return output


def prepare_dataset(
    dataset_id: str,
    raw_root: str | Path,
    processed_root: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    spec = get_dataset_spec(dataset_id)
    output = Path(processed_root) / dataset_id
    manifest_path = output / "preprocessing_manifest.json"
    if manifest_path.exists() and not overwrite:
        return manifest_path
    output.mkdir(parents=True, exist_ok=True)
    X_frame, y_raw, split, row_ids = _read_and_split(spec, Path(raw_root) / dataset_id)
    if len(X_frame) != spec.expected_rows or X_frame.shape[1] != spec.expected_features:
        raise ValueError(
            f"{dataset_id} có shape {X_frame.shape}, cần "
            f"({spec.expected_rows}, {spec.expected_features})"
        )
    numeric = X_frame.select_dtypes(include=["number", "bool"]).columns.tolist()
    categorical = [column for column in X_frame.columns if column not in numeric]
    preprocessor = ColumnTransformer([
        (
            "numeric",
            Pipeline([("imputer", SimpleImputer(strategy="median")), ("scale", StandardScaler())]),
            numeric,
        ),
        (
            "categorical",
            Pipeline([
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False, dtype=np.float32)),
            ]),
            categorical,
        ),
    ], remainder="drop", sparse_threshold=0.0)
    train_idx = split["train"]
    preprocessor.fit(X_frame.iloc[train_idx])
    label_encoder = LabelEncoder().fit(np.asarray(y_raw)[train_idx])
    if len(label_encoder.classes_) != spec.expected_classes:
        raise ValueError(
            f"Train có {len(label_encoder.classes_)} lớp, cần {spec.expected_classes}"
        )
    encoded_y = label_encoder.transform(np.asarray(y_raw)).astype(np.int64)
    for split_name, indices in split.items():
        transformed = np.asarray(preprocessor.transform(X_frame.iloc[indices]), dtype=np.float32)
        np.save(output / f"X_{split_name}.npy", transformed)
        np.save(output / f"y_{split_name}.npy", encoded_y[indices])
        np.save(output / f"row_ids_{split_name}.npy", row_ids[indices])
    joblib.dump({"features": preprocessor, "labels": label_encoder}, output / "preprocessor.joblib")
    split_manifest = {
        "dataset_id": dataset_id,
        "split_seed": SPLIT_SEED,
        "split_policy": spec.split_policy,
        "rows": {name: int(len(indices)) for name, indices in split.items()},
        "row_id_overlap": _overlap_audit(row_ids, split),
        "class_counts": {
            name: _class_counts(encoded_y[indices]) for name, indices in split.items()
        },
    }
    atomic_json(output / "split_manifest.json", split_manifest)
    atomic_json(output / "schema.json", {
        "dataset_id": dataset_id,
        "raw_columns": X_frame.columns.tolist(),
        "numeric_columns": numeric,
        "categorical_columns": categorical,
        "processed_columns": preprocessor.get_feature_names_out().tolist(),
        "label_values": [str(value) for value in label_encoder.classes_],
    })
    files = sorted(path for path in output.iterdir() if path.is_file())
    atomic_json(manifest_path, {
        "status": "prepared",
        "dataset": asdict(spec),
        "fit_scope": "preprocessor and label encoder fitted on train only",
        "artifacts_sha256": {path.name: sha256_file(path) for path in files},
    })
    return manifest_path


def load_processed(dataset_id: str, processed_root: str | Path, mmap: bool = True) -> dict[str, Any]:
    root = Path(processed_root) / dataset_id
    mode = "r" if mmap else None
    result: dict[str, Any] = {}
    for split in ("train", "dev", "test"):
        result[f"X_{split}"] = np.load(root / f"X_{split}.npy", mmap_mode=mode)
        result[f"y_{split}"] = np.load(root / f"y_{split}.npy", mmap_mode=mode)
        result[f"row_ids_{split}"] = np.load(root / f"row_ids_{split}.npy", mmap_mode=mode)
    result["split_manifest"] = json.loads((root / "split_manifest.json").read_text(encoding="utf-8"))
    return result


def _read_and_split(spec: DatasetSpec, raw_dir: Path):
    if spec.dataset_id == "adult_uci2_v1":
        return _adult(raw_dir)
    if spec.dataset_id == "letter_uci59_v1":
        return _letter(raw_dir)
    if spec.dataset_id == "covertype_uci31_v1":
        return _covertype(raw_dir)
    if spec.dataset_id == "creditcard_ulb2013_v1":
        return _credit(raw_dir)
    if spec.dataset_id in {"jannis_openml41168_v1", "helena_openml41169_v1"}:
        data_id = 41168 if "jannis" in spec.dataset_id else 41169
        bunch = fetch_openml(data_id=data_id, as_frame=True, parser="auto")
        X, y = bunch.data, bunch.target
        split = _stratified_split(np.asarray(y), SPLIT_SEED)
        return X, y, split, np.arange(len(X), dtype=np.int64)
    raise KeyError(spec.dataset_id)


def _find(raw_dir: Path, filename: str) -> Path:
    matches = list(raw_dir.rglob(filename))
    if len(matches) != 1:
        raise FileNotFoundError(f"Cần đúng một file {filename} trong {raw_dir}")
    return matches[0]


def _adult(raw_dir: Path):
    columns = [
        "age", "workclass", "fnlwgt", "education", "education_num", "marital_status",
        "occupation", "relationship", "race", "sex", "capital_gain", "capital_loss",
        "hours_per_week", "native_country", "income",
    ]
    train = pd.read_csv(_find(raw_dir, "adult.data"), names=columns, skipinitialspace=True, na_values="?")
    test = pd.read_csv(_find(raw_dir, "adult.test"), names=columns, skipinitialspace=True, na_values="?", comment="|")
    test["income"] = test["income"].astype(str).str.rstrip(".")
    frame = pd.concat([train, test], ignore_index=True)
    train_pool = np.arange(len(train))
    train_idx, dev_idx = train_test_split(
        train_pool, test_size=0.15, stratify=train["income"], random_state=SPLIT_SEED
    )
    split = {"train": train_idx, "dev": dev_idx, "test": np.arange(len(train), len(frame))}
    return frame.drop(columns="income"), frame["income"], split, np.arange(len(frame), dtype=np.int64)


def _letter(raw_dir: Path):
    features = [f"stat_{index:02d}" for index in range(1, 17)]
    frame = pd.read_csv(_find(raw_dir, "letter-recognition.data"), names=["target", *features])
    train_idx, dev_idx = train_test_split(
        np.arange(16_000), test_size=0.15, stratify=frame.loc[:15_999, "target"], random_state=SPLIT_SEED
    )
    split = {"train": train_idx, "dev": dev_idx, "test": np.arange(16_000, 20_000)}
    return frame[features], frame["target"], split, np.arange(len(frame), dtype=np.int64)


def _covertype(raw_dir: Path):
    frame = pd.read_csv(_find(raw_dir, "covtype.data.gz"), header=None)
    X, y = frame.iloc[:, :-1], frame.iloc[:, -1]
    split = _duplicate_group_split(X, y, SPLIT_SEED)
    return X, y, split, np.arange(len(frame), dtype=np.int64)


def _credit(raw_dir: Path):
    frame = pd.read_csv(_find(raw_dir, "creditcard.csv"))
    X, y = frame.drop(columns="Class"), frame["Class"]
    split = _duplicate_group_split(X, y, SPLIT_SEED)
    return X, y, split, np.arange(len(frame), dtype=np.int64)


def _stratified_split(y: np.ndarray, seed: int) -> dict[str, np.ndarray]:
    indices = np.arange(len(y))
    train, holdout = train_test_split(indices, test_size=0.30, stratify=y, random_state=seed)
    dev, test = train_test_split(holdout, test_size=0.50, stratify=y[holdout], random_state=seed)
    return {"train": train, "dev": dev, "test": test}


def _duplicate_group_split(X: pd.DataFrame, y: pd.Series, seed: int) -> dict[str, np.ndarray]:
    joined = X.copy()
    joined["__target__"] = np.asarray(y)
    group_hash = pd.util.hash_pandas_object(joined, index=False).to_numpy(dtype=np.uint64)
    table = pd.DataFrame({"group": group_hash, "label": np.asarray(y)}).drop_duplicates("group")
    groups = table["group"].to_numpy()
    labels = table["label"].to_numpy()
    train_groups, holdout_groups = train_test_split(
        groups, test_size=0.30, stratify=labels, random_state=seed
    )
    label_map = dict(zip(groups.tolist(), labels.tolist()))
    holdout_labels = np.asarray([label_map[int(group)] for group in holdout_groups])
    dev_groups, test_groups = train_test_split(
        holdout_groups, test_size=0.50, stratify=holdout_labels, random_state=seed
    )
    return {
        "train": np.flatnonzero(np.isin(group_hash, train_groups)),
        "dev": np.flatnonzero(np.isin(group_hash, dev_groups)),
        "test": np.flatnonzero(np.isin(group_hash, test_groups)),
    }


def _overlap_audit(row_ids: np.ndarray, split: dict[str, np.ndarray]) -> dict[str, int]:
    return {
        "train_dev": len(set(row_ids[split["train"]]) & set(row_ids[split["dev"]])),
        "train_test": len(set(row_ids[split["train"]]) & set(row_ids[split["test"]])),
        "dev_test": len(set(row_ids[split["dev"]]) & set(row_ids[split["test"]])),
    }


def _class_counts(y: np.ndarray) -> dict[str, int]:
    labels, counts = np.unique(y, return_counts=True)
    return {str(int(label)): int(count) for label, count in zip(labels, counts)}

