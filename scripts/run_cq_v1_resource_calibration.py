"""Đo QĐ16 trên train CQ v1: 50k/200k/800k, ba lần mỗi cỡ.

Mỗi replicate lấy mẫu phân tầng phase×class chỉ từ train, rồi đo toàn bộ đường
chọn của selector. Với LRQ-SQ, thời gian gồm cả tạo OOF-LR train-only vì đây là
chi phí thực tế của selector. Script không đọc dev/test và không dùng operation
count để loại run. Kết quả ghi observation thật, fit log--log và gate 3 giờ.
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np
import psutil
from sklearn.model_selection import train_test_split

from skq_exp.artifacts import atomic_json
from skq_exp.experiments.resource_calibration import (
    CALIBRATION_ROWS,
    CalibrationObservation,
    DeviceMetadata,
    fit_scaling_model,
    gate_decision,
)
from skq_exp.methods import build_selector
from skq_exp.methods.proposed.query_losses import make_oof_query_losses


METHODS = ("skq_pc", "skq_pc_lrq_sq", "skq_pc_r")


def _observation_payload(observations: list[CalibrationObservation]) -> list[dict[str, Any]]:
    return [
        {**item.__dict__, "device": item.device.__dict__}
        for item in observations
    ]


def _load_observations(
    path: Path,
    *,
    method_id: str,
    environment_id: str,
) -> list[CalibrationObservation]:
    """Nạp checkpoint chỉ khi method/environment khớp, không trộn máy đo."""
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Checkpoint không phải list: {path}")
    observations = []
    seen = set()
    for row in payload:
        device = DeviceMetadata(**row["device"])
        observation = CalibrationObservation(
            **{key: value for key, value in row.items() if key != "device"},
            device=device,
        )
        observation.validate()
        if observation.selector_id != method_id:
            raise ValueError(f"Checkpoint {path} chứa selector khác: {observation.selector_id}")
        if observation.device.environment_id != environment_id:
            raise ValueError(
                "Không resume calibration trên environment khác: "
                f"{observation.device.environment_id} != {environment_id}"
            )
        key = (observation.rows, observation.replicate)
        if key in seen:
            raise ValueError(f"Checkpoint trùng observation {key}: {path}")
        seen.add(key)
        observations.append(observation)
    return observations


def _gpu() -> tuple[str | None, int | None, int]:
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            check=True, capture_output=True, text=True,
        )
        rows = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        if not rows:
            return None, None, 0
        name, mib = [item.strip() for item in rows[0].split(",", maxsplit=1)]
        return name, int(float(mib) * 1024 ** 2), len(rows)
    except (FileNotFoundError, subprocess.SubprocessError, ValueError):
        return None, None, 0


def _peak_rss(call: Callable[[], Any]) -> tuple[Any, float, int]:
    process = psutil.Process()
    peak = process.memory_info().rss
    stop = threading.Event()

    def sample() -> None:
        nonlocal peak
        while not stop.wait(0.05):
            peak = max(peak, process.memory_info().rss)

    worker = threading.Thread(target=sample, daemon=True)
    worker.start()
    started = time.perf_counter()
    try:
        result = call()
    finally:
        elapsed = time.perf_counter() - started
        stop.set()
        worker.join(timeout=1.0)
        peak = max(peak, process.memory_info().rss)
    return result, elapsed, int(peak)


def _stratified_indices(y: np.ndarray, phase: np.ndarray, rows: int, seed: int) -> np.ndarray:
    if rows >= len(y):
        return np.arange(len(y), dtype=np.int64)
    strata = np.char.add(np.char.add(phase.astype(str), ":"), y.astype(str))
    all_index = np.arange(len(y), dtype=np.int64)
    selected, _ = train_test_split(
        all_index, train_size=rows, random_state=seed, shuffle=True, stratify=strata,
    )
    return np.sort(selected.astype(np.int64))


def _run_selector(
    method_id: str,
    X_selector: np.ndarray,
    X_learner: np.ndarray,
    y: np.ndarray,
    phase: np.ndarray,
    seed: int,
    budget: float,
    max_threads: int,
):
    options = {"n_components": 256, "query_alpha": 0.5, "oof_folds": 5}
    query = None
    query_meta = None
    if method_id == "skq_pc_lrq_sq":
        query, query_meta = make_oof_query_losses(
            X_learner, y, ("lr",), seed=seed, folds=5, max_threads=max_threads,
        )
    selector = build_selector(method_id, seed, options=options)
    return selector.select(
        X_selector, y, budget,
        phases=phase,
        row_ids=np.arange(len(y), dtype=np.int64),
        query_features=query,
        query_metadata=query_meta,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--processed-root", default="data/processed")
    parser.add_argument("--dataset", default="course_quality_v1")
    parser.add_argument("--output", default="artifacts/cq_v1_m0_resource_calibration")
    parser.add_argument("--budget-ratio", type=float, default=0.02)
    parser.add_argument("--method", action="append", choices=METHODS)
    parser.add_argument("--max-threads", type=int, default=4)
    parser.add_argument("--replicates", type=int, default=3)
    parser.add_argument(
        "--resume", action="store_true",
        help="Tiếp tục từ observations_<method>.json trên đúng environment.",
    )
    args = parser.parse_args()
    if args.replicates != 3:
        raise ValueError("QĐ16 yêu cầu đúng ba replicate; không giảm trong evidence M0")
    data_root = Path(args.processed_root).resolve() / args.dataset
    X_learner_all = np.load(data_root / "X_train.npy", mmap_mode="r")
    X_selector_all = np.load(data_root / "X_selector_train.npy", mmap_mode="r")
    y_all = np.load(data_root / "y_train.npy", mmap_mode="r")
    phase_all = np.load(data_root / "phase_train.npy", mmap_mode="r")
    if len(X_learner_all) != len(X_selector_all) or len(X_learner_all) < max(CALIBRATION_ROWS):
        raise ValueError(
            f"Pool learner/selector không hợp lệ: {len(X_learner_all):,}/{len(X_selector_all):,}; "
            f"cần ít nhất {max(CALIBRATION_ROWS):,}"
        )
    gpu_name, vram_bytes, gpu_count = _gpu()
    device = DeviceMetadata(
        cpu=platform.processor() or platform.machine(), gpu=gpu_name,
        ram_bytes=int(psutil.virtual_memory().total), vram_bytes=vram_bytes,
        max_threads=args.max_threads,
        environment_id=f"{platform.node()}-{platform.python_version()}-{gpu_name or 'cpu'}",
        provider="kaggle" if Path("/kaggle").exists() else "local",
        gpu_count=gpu_count,
        accelerator_policy="allocated_t4_selector_may_be_cpu_bound" if gpu_count else "cpu",
    )
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    methods = tuple(args.method or METHODS)
    all_results = {}
    for method_id in methods:
        checkpoint = output / f"observations_{method_id}.json"
        observations = (
            _load_observations(
                checkpoint, method_id=method_id,
                environment_id=device.environment_id,
            )
            if args.resume else []
        )
        completed = {(item.rows, item.replicate) for item in observations}
        print(
            f"START method={method_id} resumed_observations={len(observations)}",
            flush=True,
        )
        for rows in CALIBRATION_ROWS:
            missing_replicates = [
                replicate for replicate in range(1, 4)
                if (rows, replicate) not in completed
            ]
            if not missing_replicates:
                print(f"SKIP method={method_id} rows={rows} reason=checkpoint_complete", flush=True)
                continue
            print(f"WARMUP_START method={method_id} rows={rows}", flush=True)
            warm_index = _stratified_indices(np.asarray(y_all), np.asarray(phase_all), min(10_000, rows), 9900 + rows)
            _, warm_seconds, _ = _peak_rss(lambda: _run_selector(
                method_id,
                np.asarray(X_selector_all[warm_index]), np.asarray(X_learner_all[warm_index]),
                np.asarray(y_all[warm_index]),
                np.asarray(phase_all[warm_index]), 999, args.budget_ratio, args.max_threads,
            ))
            print(
                f"WARMUP_DONE method={method_id} rows={rows} seconds={warm_seconds:.3f}",
                flush=True,
            )
            for replicate in missing_replicates:
                seed = 11 + replicate + rows
                print(
                    f"RUN_START method={method_id} rows={rows} replicate={replicate} seed={seed}",
                    flush=True,
                )
                index = _stratified_indices(np.asarray(y_all), np.asarray(phase_all), rows, seed)
                X_selector = np.asarray(X_selector_all[index])
                X_learner = np.asarray(X_learner_all[index])
                y = np.asarray(y_all[index])
                phase = np.asarray(phase_all[index])
                result, steady, peak_rss = _peak_rss(lambda: _run_selector(
                    method_id, X_selector, X_learner, y, phase, seed,
                    args.budget_ratio, args.max_threads,
                ))
                observation = CalibrationObservation(
                    selector_id=method_id, rows=rows,
                    budget_rows=max(1, int(np.floor(rows * args.budget_ratio))),
                    replicate=replicate, warmup_seconds=warm_seconds,
                    steady_seconds=steady, peak_rss_bytes=peak_rss,
                    peak_vram_bytes=None, device=device,
                    status="success" if result.status == "success" else result.status,
                )
                observations.append(observation)
                observations.sort(key=lambda item: (item.rows, item.replicate))
                atomic_json(checkpoint, _observation_payload(observations))
                print(
                    f"RUN_DONE method={method_id} rows={rows} replicate={replicate} "
                    f"status={result.status} seconds={steady:.3f} peak_rss={peak_rss}",
                    flush=True,
                )
        fitted = fit_scaling_model(tuple(observations), target_rows=len(X_learner_all))
        decision = gate_decision(fitted, supports_sharding=method_id in {"skq_pc", "skq_pc_r"})
        all_results[method_id] = {"fit": fitted, "decision": decision}
        atomic_json(output / f"resource_fit_{method_id}.json", all_results[method_id])
        print(
            f"METHOD_DONE method={method_id} decision={decision['decision']} "
            f"upper_seconds={decision.get('upper_prediction_seconds')}",
            flush=True,
        )
    atomic_json(output / "resource_decision_all.json", {
        "schema_version": 1,
        "test_data_read": False,
        "calibration_rows": list(CALIBRATION_ROWS),
        "replicates": 3,
        "budget_ratio": args.budget_ratio,
        "target_rows": int(len(X_learner_all)),
        "selector_feature_count": int(X_selector_all.shape[1]),
        "learner_feature_count": int(X_learner_all.shape[1]),
        "methods": all_results,
    })
    print(json.dumps({method: value["decision"] for method, value in all_results.items()}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
