"""Tính UL/EC dev từ prediction artifacts CQ v1, không truy cập test.

Prediction cấp dòng được ghép với Parquet dev theo đúng thứ tự adapter và chỉ
ghi dưới ``artifacts/privacy`` (đã ignore). Báo cáo tổng hợp không chứa ID.
``course_id_equals_root`` chỉ được dùng sau khi nhóm dữ liệu xác nhận bằng văn
bản; chế độ provisional tạo evidence phát triển nhưng không mở confirmatory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from skq_exp.training.course_metrics import class_conditional_means, cq_endpoints


PHASE_BY_EVAL = {f"dev_phase{index}": f"P{index}" for index in range(1, 5)}
LABEL_TO_INT = {"E": 0, "G": 1, "A": 2}


def _experiment_root(artifact_root: Path, experiment_id: str) -> Path:
    """Trả đúng canonical run root mà experiment runner đang ghi."""
    return artifact_root / "experiments" / experiment_id


def _opaque(values: pd.Series, namespace: str) -> np.ndarray:
    return np.asarray([
        hashlib.sha256(f"{namespace}:{value}".encode("utf-8")).hexdigest()[:24]
        for value in values.astype(str)
    ], dtype=object)


def _common_key(manifest: dict[str, Any]) -> tuple[str, str, int, str, int]:
    return (
        str(manifest["dataset_id"]), str(manifest["method_id"]),
        int(manifest["selector_seed"]), str(manifest["learner_id"]),
        int(manifest["model_seed"]),
    )


def compute(
    source: Path,
    artifact_root: Path,
    experiment_id: str,
    *,
    n_min: int,
    root_policy: str,
    target_q: str,
    target_y: str,
) -> dict[str, Any]:
    experiment = _experiment_root(artifact_root, experiment_id)
    manifests = []
    for path in experiment.rglob("manifest.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("evaluation_split") in PHASE_BY_EVAL and (path.parent / "predictions.npz").is_file():
            manifests.append((path.parent, payload))
    if not manifests:
        raise FileNotFoundError(f"Không tìm thấy dev predictions trong {experiment}")

    train = pd.read_parquet(
        source / "model_ready" / "P1" / "train.parquet",
        columns=[target_q, target_y],
    ).rename(columns={target_q: "q", target_y: "y"})
    mu = class_conditional_means(train)
    grouped: dict[tuple[str, str, int, str, int], list[tuple[Path, dict[str, Any]]]] = {}
    for item in manifests:
        grouped.setdefault(_common_key(item[1]), []).append(item)

    private_root = artifact_root / "privacy" / experiment_id
    private_root.mkdir(parents=True, exist_ok=True)
    summaries = []
    for key, items in sorted(grouped.items()):
        by_eval = {manifest["evaluation_split"]: (run_dir, manifest) for run_dir, manifest in items}
        missing = sorted(set(PHASE_BY_EVAL) - set(by_eval))
        if missing:
            summaries.append({"identity": list(key), "status": "incomplete", "missing": missing})
            continue
        endpoint_run_id = hashlib.sha256(json.dumps(key).encode("utf-8")).hexdigest()[:20]
        frames = []
        for eval_name, phase in PHASE_BY_EVAL.items():
            run_dir, manifest = by_eval[eval_name]
            prediction = np.load(run_dir / "predictions.npz")
            if "y_prob" not in prediction:
                raise ValueError(f"{run_dir} thiếu y_prob; config phải save_probabilities=true")
            source_frame = pd.read_parquet(
                source / "model_ready" / phase / "dev.parquet",
                columns=["user_id", "course_id", target_q, target_y],
            )
            y_true = source_frame[target_y].astype(str).map(LABEL_TO_INT).to_numpy(dtype=int)
            if len(source_frame) != len(prediction["y_pred"]):
                raise ValueError(f"Lệch số dòng {eval_name}: source={len(source_frame)}, prediction={len(prediction['y_pred'])}")
            if "y_true" in prediction and not np.array_equal(y_true, prediction["y_true"].astype(int)):
                raise ValueError(f"Thứ tự y_true không khớp source ở {eval_name}")
            probabilities = np.asarray(prediction["y_prob"], dtype=float)
            if probabilities.shape != (len(source_frame), 3):
                raise ValueError(f"Probability shape sai ở {eval_name}: {probabilities.shape}")
            course = _opaque(source_frame["course_id"], "course")
            learner = _opaque(source_frame["user_id"], "learner")
            frames.append(pd.DataFrame({
                "run_id": endpoint_run_id,
                "course_id": course,
                "course_root_id": course,
                "learner_id": learner,
                "phase": phase,
                "q_true": source_frame[target_q].to_numpy(dtype=float),
                "y_true": y_true,
                "y_pred": prediction["y_pred"].astype(int),
                "p_E": probabilities[:, 0], "p_G": probabilities[:, 1], "p_A": probabilities[:, 2],
            }))
        private = pd.concat(frames, ignore_index=True)
        private_path = private_root / f"{endpoint_run_id}.parquet"
        private.to_parquet(private_path, index=False)
        pcc = cq_endpoints(private, mu, n_min=n_min, mode="pcc")
        cc = cq_endpoints(private, mu, n_min=n_min, mode="cc")
        summaries.append({
            "status": "success",
            "dataset_id": key[0], "method_id": key[1], "selector_seed": key[2],
            "learner_id": key[3], "model_seed": key[4],
            "endpoint_run_id": endpoint_run_id,
            "evaluation_level": ["enrollment", "course"],
            "aggregation_primary": "PCC",
            "root_policy": root_policy,
            "confirmatory_eligible": root_policy == "course_id_equals_root",
            "n_min": n_min,
            "mu_train": mu,
            "pcc": pcc,
            "cc_sensitivity": cc,
            "private_predictions": str(private_path),
        })
    output = experiment / "cq_dev_endpoints.json"
    output.write_text(json.dumps({
        "schema_version": 1,
        "experiment_id": experiment_id,
        "split": "dev_only",
        "test_predictions_read": False,
        "root_policy": root_policy,
        "confirmatory_eligible": root_policy == "course_id_equals_root",
        "runs": summaries,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"output": str(output), "runs": len(summaries), "successful": sum(row.get("status") == "success" for row in summaries)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--artifact-root", default="artifacts")
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--n-min", type=int, default=30)
    parser.add_argument("--root-policy", choices=("provisional_course_id", "course_id_equals_root"), default="provisional_course_id")
    parser.add_argument("--target-q", default="q_alpha_1")
    parser.add_argument("--target-y", default="y_alpha_1")
    args = parser.parse_args()
    result = compute(
        Path(args.input_dir).resolve(), Path(args.artifact_root).resolve(), args.experiment_id,
        n_min=args.n_min, root_policy=args.root_policy, target_q=args.target_q, target_y=args.target_y,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
