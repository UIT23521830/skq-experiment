"""Nhập snapshot CourseQuality MED đã chia sẵn vào contract dữ liệu SKQ.

File này giữ đúng tiền xử lý đang dùng cho CourseQuality: ``label_f`` là nhãn
ba lớp; ``label`` trung gian, ID và ``euclid_to_111`` bị bỏ để tránh leakage;
chapter được tách thành ba mức. Mọi mapping categorical và median điền thiếu chỉ
được fit trên train. Val trở thành dev. Bốn test snapshot đều được lưu, còn
``X_test/y_test`` chỉ là alias vật lý của phase 4 để thỏa contract loader hiện
tại; config screening vẫn khóa test và không dùng alias này để chọn phương pháp.

Split do người dùng cung cấp hiện trùng nhiều group user-course. Manifest ghi
thẳng audit đó và không cho phép hiểu run này là bằng chứng confirmatory.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from ..artifacts import atomic_json, sha256_file
from .registry import get_dataset_spec


DATASET_ID = "course_quality_med_v1"
TARGET_COLUMN = "label_f"
LABEL_MAPPING = {"excellent": 0, "good": 1, "average": 2}
DROP_COLUMNS = {
    "label", "user_id", "course_id", "user_id_enc", "course_id_enc",
    "euclid_to_111", "phase",
}
EXPECTED_ROWS = {
    "train_med.csv": 2_637_700,
    "val_med.csv": 329_713,
    "test_med_1.csv": 329_715,
    "test_med_2.csv": 329_715,
    "test_med_3.csv": 329_715,
    "test_med_4.csv": 329_715,
}


def prepare_course_quality_snapshot(
    input_dir: str | Path,
    processed_root: str | Path,
    *,
    dataset_id: str = DATASET_ID,
    overwrite: bool = False,
    validate_expected_rows: bool = True,
) -> Path:
    """Tiền xử lý sáu CSV CourseQuality và trả đường dẫn manifest.

    Hàm đọc từng split/test snapshot lần lượt để không giữ bốn test trong RAM.
    ``overwrite`` chỉ ghi đè các file thuộc đúng thư mục dataset, không xóa thư
    mục processed chung.
    """

    spec = get_dataset_spec(dataset_id)
    if dataset_id != DATASET_ID:
        raise ValueError(f"Adapter CourseQuality không hỗ trợ dataset_id={dataset_id}")
    source = Path(input_dir).resolve()
    output = Path(processed_root).resolve() / dataset_id
    manifest_path = output / "preprocessing_manifest.json"
    if manifest_path.exists() and not overwrite:
        return manifest_path

    paths = {name: source / name for name in EXPECTED_ROWS}
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Thiếu file CourseQuality: {missing}")
    output.mkdir(parents=True, exist_ok=True)

    train_raw = pd.read_csv(paths["train_med.csv"])
    _validate_row_count("train_med.csv", len(train_raw), validate_expected_rows)
    train_groups = _group_keys(train_raw)
    raw_train_columns = train_raw.columns.tolist()
    state: dict[str, Any] = {"category_maps": {}, "numeric_fill_values": {}}
    X_train, y_train, feature_names = _transform(train_raw, state, fit=True)
    if validate_expected_rows and X_train.shape[1] != spec.expected_features:
        raise ValueError(
            f"CourseQuality có {X_train.shape[1]} feature sau xử lý, "
            f"cần đúng {spec.expected_features}"
        )
    del train_raw
    _save_split(output, "train", X_train, y_train, row_offset=0)
    train_shape = [int(value) for value in X_train.shape]
    del X_train, y_train

    val_raw = pd.read_csv(paths["val_med.csv"])
    _validate_row_count("val_med.csv", len(val_raw), validate_expected_rows)
    val_groups = _group_keys(val_raw)
    X_dev, y_dev, _ = _transform(val_raw, state, fit=False, feature_names=feature_names)
    del val_raw
    _save_split(output, "dev", X_dev, y_dev, row_offset=EXPECTED_ROWS["train_med.csv"])
    dev_shape = [int(value) for value in X_dev.shape]
    del X_dev, y_dev

    test_shapes: dict[str, list[int]] = {}
    test_group_keys: dict[int, set[int]] = {}
    test_group_labels: dict[int, dict[int, str]] = {}
    for phase in range(1, 5):
        name = f"test_med_{phase}.csv"
        raw = pd.read_csv(paths[name])
        _validate_row_count(name, len(raw), validate_expected_rows)
        test_group_keys[phase] = _group_keys(raw)
        test_group_labels[phase] = _group_labels(raw)
        X_test, y_test, _ = _transform(raw, state, fit=False, feature_names=feature_names)
        del raw
        np.save(output / f"X_test_phase{phase}.npy", X_test)
        np.save(output / f"y_test_phase{phase}.npy", y_test)
        test_shapes[str(phase)] = [int(value) for value in X_test.shape]
        if phase == 4:
            np.save(
                output / "row_ids_test.npy",
                np.arange(len(y_test), dtype=np.int64)
                + EXPECTED_ROWS["train_med.csv"] + EXPECTED_ROWS["val_med.csv"],
            )
        del X_test, y_test

    # Loader hiện cần đúng ba split. Copy phase 4 thay vì symlink để archive Kaggle
    # tự chứa đủ dữ liệu và không phụ thuộc filesystem hỗ trợ link.
    shutil.copyfile(output / "X_test_phase4.npy", output / "X_test.npy")
    shutil.copyfile(output / "y_test_phase4.npy", output / "y_test.npy")

    joblib.dump(
        {
            "target_column": TARGET_COLUMN,
            "label_mapping": LABEL_MAPPING,
            "feature_names": feature_names,
            **state,
        },
        output / "preprocessor.joblib",
    )
    group_overlap = {
        "train_dev": len(train_groups & val_groups),
        "train_test": len(train_groups & test_group_keys[1]),
        "dev_test": len(val_groups & test_group_keys[1]),
    }
    snapshots_aligned = all(
        test_group_keys[phase] == test_group_keys[1]
        and test_group_labels[phase] == test_group_labels[1]
        for phase in range(2, 5)
    )
    paper_gate = all(value == 0 for value in group_overlap.values()) and snapshots_aligned
    split_manifest = {
        "dataset_id": dataset_id,
        "split_seed": None,
        "split_policy": spec.split_policy,
        "rows": {
            "train": train_shape[0],
            "dev": dev_shape[0],
            "test_phase_1": test_shapes["1"][0],
            "test_phase_2": test_shapes["2"][0],
            "test_phase_3": test_shapes["3"][0],
            "test_phase_4": test_shapes["4"][0],
        },
        "canonical_test_alias": "test_phase_4",
        "group_definition": ["user_id_enc", "course_id_enc"],
        "group_overlap": group_overlap,
        "test_snapshots_aligned": snapshots_aligned,
        "paper_evidence_gate_passed": paper_gate,
        "warning": (
            "Run chỉ dùng để integration/debug khi group overlap khác 0; "
            "không dùng metric này làm bằng chứng confirmatory."
        ),
    }
    atomic_json(output / "split_manifest.json", split_manifest)
    atomic_json(
        output / "schema.json",
        {
            "dataset_id": dataset_id,
            "raw_train_columns": raw_train_columns,
            "processed_columns": feature_names,
            "label_values": list(LABEL_MAPPING),
            "label_mapping": LABEL_MAPPING,
            "dropped_columns": sorted(DROP_COLUMNS),
            "preprocessing_contract": "course_quality_author_methodology_train_only_fit_v1",
        },
    )
    files_before_manifest = sorted(path for path in output.iterdir() if path.is_file())
    atomic_json(
        manifest_path,
        {
            "status": "prepared",
            "dataset": {
                "dataset_id": spec.dataset_id,
                "title": spec.title,
                "provider": spec.provider,
                "source": spec.source,
                "expected_rows": spec.expected_rows,
                "expected_features": spec.expected_features,
                "expected_classes": spec.expected_classes,
                "split_policy": spec.split_policy,
            },
            "fit_scope": "categorical maps and numeric medians fitted on train only",
            "evidence_role": "integration_debug_until_group_disjoint_gate_passes",
            "raw_files_sha256": {
                name: sha256_file(path) for name, path in sorted(paths.items())
            },
            "artifacts_sha256": {
                path.name: sha256_file(path) for path in files_before_manifest
            },
        },
    )
    return manifest_path


def _validate_row_count(name: str, actual: int, enabled: bool) -> None:
    if enabled and actual != EXPECTED_ROWS[name]:
        raise ValueError(f"{name} có {actual:,} dòng, cần đúng {EXPECTED_ROWS[name]:,}")


def _split_chapter(frame: pd.DataFrame) -> pd.DataFrame:
    if "chapter" not in frame.columns:
        return frame
    parts = frame.pop("chapter").astype(str).str.split(".", expand=True)
    for level in range(3):
        values = (
            parts[level]
            if level < parts.shape[1]
            else pd.Series(0, index=frame.index, dtype=np.int64)
        )
        frame[f"chapter_{level + 1}"] = (
            pd.to_numeric(values, errors="coerce").fillna(0).astype(np.int64)
        )
    return frame


def _transform(
    frame: pd.DataFrame,
    state: dict[str, Any],
    *,
    fit: bool,
    feature_names: list[str] | None = None,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    frame = _split_chapter(frame)
    frame = frame.drop(columns=[col for col in DROP_COLUMNS if col in frame.columns])
    if TARGET_COLUMN not in frame.columns:
        raise KeyError(f"Thiếu cột nhãn {TARGET_COLUMN}")
    raw_labels = frame.pop(TARGET_COLUMN)
    labels = raw_labels.map(LABEL_MAPPING)
    if labels.isna().any():
        unknown = sorted(set(raw_labels.loc[labels.isna()].astype(str)))
        raise ValueError(f"label_f ngoài mapping: {unknown}")

    object_columns = frame.select_dtypes(include=["object"]).columns.tolist()
    for column in object_columns:
        values = frame[column].astype(str)
        if fit:
            categories = sorted(values.unique().tolist())
            state["category_maps"][column] = {
                value: index for index, value in enumerate(categories)
            }
        mapping = state["category_maps"].get(column)
        if mapping is None:
            raise ValueError(f"Cột categorical '{column}' không tồn tại trong train schema")
        frame[column] = values.map(mapping).fillna(-1).astype(np.int64)

    for column in frame.columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if fit:
        state["numeric_fill_values"] = {
            column: (0.0 if pd.isna(frame[column].median()) else float(frame[column].median()))
            for column in frame.columns
        }
        feature_names = frame.columns.tolist()
    if feature_names is None:
        raise ValueError("Thiếu feature_names đã fit từ train")
    missing = [column for column in feature_names if column not in frame.columns]
    if missing:
        raise ValueError(f"Split thiếu feature đã có trong train: {missing}")
    frame = frame[feature_names]
    for column in feature_names:
        frame[column] = frame[column].fillna(state["numeric_fill_values"][column])
    return (
        frame.to_numpy(dtype=np.float32, copy=True),
        labels.to_numpy(dtype=np.int64, copy=True),
        feature_names,
    )


def _save_split(
    output: Path,
    split: str,
    X: np.ndarray,
    y: np.ndarray,
    *,
    row_offset: int,
) -> None:
    np.save(output / f"X_{split}.npy", X)
    np.save(output / f"y_{split}.npy", y)
    np.save(
        output / f"row_ids_{split}.npy",
        np.arange(len(y), dtype=np.int64) + int(row_offset),
    )


def _group_keys(frame: pd.DataFrame) -> set[int]:
    columns = ["user_id_enc", "course_id_enc"]
    if any(column not in frame.columns for column in columns):
        raise KeyError(f"CourseQuality thiếu group columns: {columns}")
    values = pd.util.hash_pandas_object(frame[columns], index=False).to_numpy(dtype=np.uint64)
    return {int(value) for value in np.unique(values)}


def _group_labels(frame: pd.DataFrame) -> dict[int, str]:
    columns = ["user_id_enc", "course_id_enc"]
    keys = pd.util.hash_pandas_object(frame[columns], index=False).to_numpy(dtype=np.uint64)
    labels = frame[TARGET_COLUMN].astype(str).to_numpy()
    # first-label map chỉ dùng kiểm tra bốn snapshot có cùng đối tượng/nhãn.
    result: dict[int, str] = {}
    for key, label in zip(keys, labels):
        result.setdefault(int(key), str(label))
    return result
