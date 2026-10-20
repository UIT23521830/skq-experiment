"""Adapter CQ v1 enrollment-phase cho Pool B và dev/test bốn phase.

Nguồn ``phase_features_v2`` đã được nhóm dữ liệu tạo theo khóa học và có hai
nhãn alpha dùng chung X. Adapter này không tự chia lại dữ liệu, không dùng q/y
làm feature, không đưa mã định danh vào hình học và giữ test khóa ở runner.
``course_id`` tạm làm group audit vì snapshot hiện chưa có ``course_root_id``;
do đó artifact được đánh dấu development-only, không đủ điều kiện confirmatory.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from ...artifacts import atomic_json, sha256_file, stable_hash
from ..registry import get_dataset_spec
from .base import DatasetAdapter


PHASES = ("P1", "P2", "P3", "P4")
SPLITS = ("train", "dev", "test")
LABEL_MAPPING = {"E": 0, "G": 1, "A": 2}


class _CourseQualityV1Base(DatasetAdapter):
    target_column: str
    target_q_column: str

    def prepare(
        self,
        input_dir: str | Path,
        processed_root: str | Path,
        *,
        overwrite: bool = False,
        validate_expected_rows: bool = True,
    ) -> Path:
        source = Path(input_dir).resolve()
        output = Path(processed_root).resolve() / self.dataset_id
        manifest_path = output / "preprocessing_manifest.json"
        if manifest_path.exists() and not overwrite:
            return manifest_path
        if output.exists() and overwrite:
            shutil.rmtree(output)
        output.mkdir(parents=True, exist_ok=True)

        required_metadata = (
            "_SUCCESS.json", "validation.json", "feature_columns.json",
            "preprocessing.json", "run_manifest.json",
        )
        missing = [name for name in required_metadata if not (source / name).is_file()]
        if missing:
            raise FileNotFoundError(f"CQ v1 thiếu metadata nguồn: {missing}")
        validation = json.loads((source / "validation.json").read_text(encoding="utf-8"))
        failed_checks = sorted(key for key, value in validation.items() if value is False)
        if failed_checks:
            raise ValueError(f"CQ v1 validation nguồn có gate fail: {failed_checks}")

        feature_spec = json.loads(
            (source / "feature_columns.json").read_text(encoding="utf-8")
        )
        numeric = [
            column for column in feature_spec["distance_feature_columns"]
            if column != "phase_fraction"
        ]
        if len(numeric) != 56:
            raise ValueError(f"CQ v1 cần 56 feature số sau lọc, nhận {len(numeric)}")

        shapes: dict[str, dict[str, list[int]]] = {split: {} for split in SPLITS}
        class_counts: dict[str, dict[str, dict[str, int]]] = {
            split: {} for split in SPLITS
        }
        split_groups: dict[str, set[int]] = {}
        train_parts: list[np.ndarray] = []
        train_labels: list[np.ndarray] = []
        train_row_ids: list[np.ndarray] = []
        train_phases: list[np.ndarray] = []

        for phase_index, phase in enumerate(PHASES, start=1):
            for split in SPLITS:
                path = source / "model_ready" / phase / f"{split}.parquet"
                if not path.is_file():
                    raise FileNotFoundError(f"CQ v1 thiếu {path}")
                columns = [
                    "user_id", "course_id", "phase", "split",
                    self.target_column, self.target_q_column, *numeric,
                ]
                frame = pd.read_parquet(path, columns=columns)
                self._validate_frame(frame, split=split, phase=phase)
                X = frame[numeric].to_numpy(dtype=np.float32, copy=True)
                if not np.isfinite(X).all():
                    raise ValueError(f"CQ v1 có NaN/Inf sau preprocessing: {phase}/{split}")
                y = self._encode_labels(frame[self.target_column], phase, split)
                row_ids = pd.util.hash_pandas_object(
                    frame[["user_id", "course_id", "phase"]], index=False,
                ).to_numpy(dtype=np.uint64)
                course_groups = pd.util.hash_pandas_object(
                    frame[["course_id"]], index=False,
                ).to_numpy(dtype=np.uint64)
                split_groups.setdefault(split, set()).update(
                    int(value) for value in np.unique(course_groups)
                )
                shapes[split][phase] = [int(X.shape[0]), int(X.shape[1])]
                class_counts[split][phase] = self._class_counts(y)

                if split == "train":
                    train_parts.append(X)
                    train_labels.append(y)
                    train_row_ids.append(row_ids)
                    train_phases.append(
                        np.full(len(y), phase_index - 1, dtype=np.int8)
                    )
                else:
                    prefix = f"{split}_phase{phase_index}"
                    np.save(output / f"X_{prefix}.npy", X)
                    np.save(output / f"y_{prefix}.npy", y)
                    np.save(output / f"row_ids_{prefix}.npy", row_ids)
                    np.save(output / f"course_groups_{prefix}.npy", course_groups)

        X_train = np.concatenate(train_parts, axis=0)
        y_train = np.concatenate(train_labels)
        row_ids_train = np.concatenate(train_row_ids)
        phase_train = np.concatenate(train_phases)
        if len(np.unique(row_ids_train)) != len(row_ids_train):
            raise ValueError("CQ v1 Pool B có row_id trùng")
        np.save(output / "X_train.npy", X_train)
        np.save(output / "X_selector_train.npy", X_train)
        np.save(output / "y_train.npy", y_train)
        np.save(output / "row_ids_train.npy", row_ids_train)
        np.save(output / "phase_train.npy", phase_train)

        # Alias tương thích runner: dev/test canonical là P4; đánh giá CQ v1 dev
        # thực tế vẫn dùng đủ dev_phase1..4 qua _evaluation_splits.
        for split in ("dev", "test"):
            for stem in ("X", "y", "row_ids"):
                shutil.copy2(
                    output / f"{stem}_{split}_phase4.npy",
                    output / f"{stem}_{split}.npy",
                )

        expected = get_dataset_spec(self.dataset_id)
        if validate_expected_rows:
            phase_rows = {
                split: {shapes[split][phase][0] for phase in PHASES}
                for split in SPLITS
            }
            if any(len(values) != 1 for values in phase_rows.values()):
                raise ValueError(f"CQ v1 số dòng không đồng nhất giữa phase: {phase_rows}")
            unique_total = sum(next(iter(values)) for values in phase_rows.values())
            if unique_total != expected.expected_rows:
                raise ValueError(
                    f"CQ v1 có {unique_total:,} enrollment, cần {expected.expected_rows:,}"
                )

        overlaps = {
            "train_dev": len(split_groups["train"] & split_groups["dev"]),
            "train_test": len(split_groups["train"] & split_groups["test"]),
            "dev_test": len(split_groups["dev"] & split_groups["test"]),
        }
        if any(overlaps.values()):
            raise ValueError(f"CQ v1 course_id overlap giữa split: {overlaps}")

        contract = {
            "schema_version": 1,
            "numeric_feature_columns": numeric,
            "selector_columns": numeric,
            "learner_columns": numeric,
            "excluded_from_X": [
                "user_id", "course_id", "phase", "split", "enroll_time",
                "cutoff_time", "phase_fraction", *feature_spec["categorical_features"],
                *feature_spec["target_columns"],
            ],
            "target_column": self.target_column,
            "label_mapping": LABEL_MAPPING,
            "source_preprocessing_scope": feature_spec.get("preprocessing_scope"),
            "group_unit": "course_id_provisional",
            "required_confirmatory_group_unit": "course_root_id",
            "confirmatory_eligible": False,
            "deviation": "Snapshot thiếu course_root_id; chỉ development evidence.",
        }
        contract["contract_hash"] = stable_hash(contract)
        atomic_json(output / "feature_contract.json", contract)
        atomic_json(output / "schema.json", contract)
        atomic_json(output / "split_manifest.json", {
            "dataset_id": self.dataset_id,
            "split_policy": expected.split_policy,
            "pool_b_rows": int(len(y_train)),
            "rows_by_split_phase": shapes,
            "class_counts": class_counts,
            "course_id_overlap": overlaps,
            "group_unit": "course_id_provisional",
            "test_locked": True,
            "confirmatory_eligible": False,
        })
        joblib.dump({
            "source": "phase_features_v2/model_ready",
            "feature_columns": numeric,
            "target_column": self.target_column,
            "label_mapping": LABEL_MAPPING,
            "transform": "source train-only per-phase preprocessing; no refit in adapter",
        }, output / "preprocessor.joblib")

        source_files = [source / name for name in required_metadata]
        source_files.extend(
            source / "model_ready" / phase / f"{split}.parquet"
            for phase in PHASES for split in SPLITS
        )
        files_before_manifest = sorted(path for path in output.iterdir() if path.is_file())
        atomic_json(manifest_path, {
            "status": "prepared_development_only",
            "dataset": asdict(expected),
            "adapter": f"{type(self).__module__}.{type(self).__qualname__}",
            "fit_scope": "source preprocessing fitted on train only, separately by phase",
            "target_policy": "alpha=1 primary" if self.target_column == "y_alpha_1" else "alpha=0.1 sensitivity",
            "test_locked": True,
            "confirmatory_eligible": False,
            "blocker": "course_root_id absent from supplied snapshot",
            "raw_files_sha256": {
                path.relative_to(source).as_posix(): sha256_file(path)
                for path in source_files
            },
            "artifacts_sha256": {
                path.name: sha256_file(path) for path in files_before_manifest
            },
        })
        return manifest_path

    def _validate_frame(self, frame: pd.DataFrame, *, split: str, phase: str) -> None:
        if set(frame["split"].astype(str).unique()) != {split}:
            raise ValueError(f"CQ v1 split sai trong {phase}/{split}")
        if set(frame["phase"].astype(str).unique()) != {phase}:
            raise ValueError(f"CQ v1 phase sai trong {phase}/{split}")
        if frame[["user_id", "course_id", self.target_column]].isna().any().any():
            raise ValueError(f"CQ v1 thiếu key/target trong {phase}/{split}")
        if frame.duplicated(["user_id", "course_id", "phase"]).any():
            raise ValueError(f"CQ v1 trùng enrollment-phase trong {phase}/{split}")

    @staticmethod
    def _encode_labels(values: pd.Series, phase: str, split: str) -> np.ndarray:
        unknown = sorted(set(values.astype(str)) - set(LABEL_MAPPING))
        if unknown:
            raise ValueError(f"CQ v1 có label lạ {unknown} trong {phase}/{split}")
        return values.astype(str).map(LABEL_MAPPING).to_numpy(dtype=np.int64)

    @staticmethod
    def _class_counts(y: np.ndarray) -> dict[str, int]:
        labels, counts = np.unique(y, return_counts=True)
        return {str(int(label)): int(count) for label, count in zip(labels, counts)}


class CourseQualityV1Adapter(_CourseQualityV1Base):
    """Nhãn chính theo đóng góp AFELO alpha=1."""

    dataset_id = "course_quality_v1"
    target_column = "y_alpha_1"
    target_q_column = "q_alpha_1"


class CourseQualityV1Afelo01Adapter(_CourseQualityV1Base):
    """Sensitivity label theo đóng góp AFELO alpha=0.1."""

    dataset_id = "course_quality_v1_afelo0p1"
    target_column = "y_alpha_0p1"
    target_q_column = "q_alpha_0p1"
