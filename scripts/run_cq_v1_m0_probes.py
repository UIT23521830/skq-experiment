"""Chạy các probe M0 khả thi từ snapshot model-ready, chỉ trên dev.

D02 kiểm course-ID và teacher/school code; D04 huấn luyện XGBoost với nhãn train
hoán vị; D05 tính majority baseline. Không probe nào đọc dự đoán hoặc metric test.
Missingness AUC và cutoff-20 vẫn cần raw/pre-imputation source nên không được giả
là PASS từ snapshot đã điền khuyết.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder


PHASES = ("P1", "P2", "P3", "P4")
LABEL_TO_INT = {"E": 0, "G": 1, "A": 2}


def _labels(frame: pd.DataFrame, column: str) -> np.ndarray:
    return frame[column].astype(str).map(LABEL_TO_INT).to_numpy(dtype=int)


def _majority(y_train: np.ndarray, y_dev: np.ndarray) -> dict:
    label = int(np.bincount(y_train, minlength=3).argmax())
    prediction = np.full(len(y_dev), label, dtype=int)
    return {"majority_label": label, "macro_f1": float(f1_score(y_dev, prediction, labels=[0, 1, 2], average="macro", zero_division=0))}


def _categorical_probe(train: pd.DataFrame, dev: pd.DataFrame, columns: list[str], target: str) -> dict:
    model = make_pipeline(
        ColumnTransformer([("id", OneHotEncoder(handle_unknown="ignore", dtype=np.float32), columns)]),
        LogisticRegression(max_iter=1000, solver="lbfgs", class_weight=None),
    )
    y_train = _labels(train, target)
    y_dev = _labels(dev, target)
    model.fit(train[columns], y_train)
    prediction = model.predict(dev[columns])
    unseen = {
        column: float((~dev[column].astype(str).isin(set(train[column].astype(str)))).mean())
        for column in columns
    }
    return {
        "columns": columns,
        "macro_f1": float(f1_score(y_dev, prediction, labels=[0, 1, 2], average="macro", zero_division=0)),
        "unseen_rate_dev": unseen,
    }


def _shuffle_xgb(source: Path, target: str, feature_columns: list[str], seed: int) -> dict:
    try:
        from xgboost import XGBClassifier
    except ImportError as error:
        raise RuntimeError("D04 cần cài extra boosting/xgboost") from error
    train_frames = [pd.read_parquet(source / "model_ready" / phase / "train.parquet", columns=[target, *feature_columns]) for phase in PHASES]
    train = pd.concat(train_frames, ignore_index=True)
    X_train = train[feature_columns].to_numpy(dtype=np.float32)
    y_train = _labels(train, target)
    shuffled = np.random.default_rng(seed).permutation(y_train)
    model = XGBClassifier(
        n_estimators=300, max_depth=4, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, tree_method="hist",
        device="cuda", random_state=seed, n_jobs=4, eval_metric="mlogloss",
    )
    model.fit(X_train, shuffled)
    per_phase = {}
    for phase in PHASES:
        dev = pd.read_parquet(source / "model_ready" / phase / "dev.parquet", columns=[target, *feature_columns])
        y_dev = _labels(dev, target)
        pred = model.predict(dev[feature_columns].to_numpy(dtype=np.float32)).astype(int)
        per_phase[phase] = float(f1_score(y_dev, pred, labels=[0, 1, 2], average="macro", zero_division=0))
    return {"seed": seed, "learner": "xgb", "train_labels_permuted": True, "macro_f1_by_phase": per_phase, "macro_f1_mean": float(np.mean(list(per_phase.values())))}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output", default="artifacts/cq_v1_m0_probes.json")
    parser.add_argument("--target", default="y_alpha_1")
    parser.add_argument("--seed", type=int, default=20261021)
    parser.add_argument("--skip-shuffle", action="store_true")
    args = parser.parse_args()
    source = Path(args.input_dir).resolve()
    feature_spec = json.loads((source / "feature_columns.json").read_text(encoding="utf-8"))
    features = [column for column in feature_spec["distance_feature_columns"] if column != "phase_fraction"]
    train = pd.read_parquet(
        source / "model_ready" / "P4" / "train.parquet",
        columns=["course_id", "learner_code", "teacher_set_code", "school_set_code", args.target],
    )
    dev = pd.read_parquet(
        source / "model_ready" / "P4" / "dev.parquet",
        columns=["course_id", "learner_code", "teacher_set_code", "school_set_code", args.target],
    )
    y_train = _labels(train, args.target)
    y_dev = _labels(dev, args.target)
    majority = _majority(y_train, y_dev)
    course_probe = _categorical_probe(train, dev, ["course_id"], args.target)
    operational_probe = _categorical_probe(train, dev, ["teacher_set_code", "school_set_code"], args.target)
    learner_unseen = float((~dev["learner_code"].astype(str).isin(set(train["learner_code"].astype(str)))).mean())
    result = {
        "schema_version": 1,
        "split": "dev_only",
        "test_read": False,
        "D02": {
            "course_id_probe": course_probe,
            "teacher_school_probe": operational_probe,
            "new_learner_rate_dev": learner_unseen,
            "majority_reference": majority,
        },
        "D04": {"status": "SKIPPED_BY_FLAG"} if args.skip_shuffle else _shuffle_xgb(source, args.target, features, args.seed),
        "D05": {
            phase: _majority(
                _labels(pd.read_parquet(source / "model_ready" / phase / "train.parquet", columns=[args.target]), args.target),
                _labels(pd.read_parquet(source / "model_ready" / phase / "dev.parquet", columns=[args.target]), args.target),
            )
            for phase in PHASES
        },
        "D03": {"status": "BLOCKED_RAW_PREIMPUTATION_REQUIRED"},
        "D06": {"status": "BLOCKED_RAW_EVENT_TIMESTAMPS_REQUIRED"},
    }
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), "D02_course_macro_f1": course_probe["macro_f1"], "D02_majority_macro_f1": majority["macro_f1"], "D04": result["D04"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
