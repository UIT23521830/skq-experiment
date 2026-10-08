"""File này train một learner trên selection và đánh giá trên tập được chỉ định.

Nó giữ cùng cấu hình model giữa các phương pháp, truyền đúng sample weight và lưu
prediction trước khi tính metric. Dev hoặc test được caller chọn rõ; evaluator
không tự dùng test để early stopping hay tuning.
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np
import psutil

from ..methods.result import SelectionResult
from ..methods.synthetic.result import GeneratedDatasetResult
from .learners import build_learner
from .metrics import compute_all_metrics
from .weights import balanced_class_weights, effective_sample_weights


def evaluate_selection(
    selection: SelectionResult,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_eval: np.ndarray,
    y_eval: np.ndarray,
    *,
    learner_id: str,
    model_seed: int = 42,
    learner_params: dict[str, Any] | None = None,
    X_inner_val: np.ndarray | None = None,
    y_inner_val: np.ndarray | None = None,
    horizons: np.ndarray | None = None,
    max_threads: int = 4,
) -> tuple[Any, dict[str, Any], dict[str, np.ndarray]]:
    if selection.status != "success":
        raise RuntimeError(f"Không thể train từ selection status={selection.status}")
    selected_X = X_train[selection.indices]
    selected_y = y_train[selection.indices]
    class_weights = balanced_class_weights(y_train)
    sample_weight = effective_sample_weights(selected_y, selection.weights, class_weights)
    labels = np.unique(y_train)
    learner = build_learner(
        learner_id,
        seed=model_seed,
        input_dim=X_train.shape[1],
        n_classes=len(labels),
        params=learner_params,
        max_threads=max_threads,
    )
    process = psutil.Process()
    cpu_before = sum(process.cpu_times()[:2])
    rss_before = process.memory_info().rss
    io_before = _io_bytes(process)
    fit_started = time.perf_counter()
    if learner_id == "mlp":
        eval_set = None if X_inner_val is None else (X_inner_val, y_inner_val)
        learner.fit(selected_X, selected_y, sample_weight=sample_weight, eval_set=eval_set)
    else:
        learner.fit(selected_X, selected_y, sample_weight=sample_weight)
    fit_time = time.perf_counter() - fit_started
    predict_started = time.perf_counter()
    y_pred = learner.predict(X_eval)
    y_prob = learner.predict_proba(X_eval) if hasattr(learner, "predict_proba") else None
    predict_time = time.perf_counter() - predict_started
    cpu_after = sum(process.cpu_times()[:2])
    rss_after = process.memory_info().rss
    io_after = _io_bytes(process)
    cost = {
        "selection_seconds": selection.timings.get("total", selection.timings.get("select")),
        "fit_seconds": fit_time,
        "predict_seconds": predict_time,
        "realized_rows": selection.realized_rows,
        "requested_rows": selection.requested_rows,
        "total_seconds": (selection.timings.get("total") or 0.0) + fit_time + predict_time,
        "cpu_seconds_fit_predict": cpu_after - cpu_before,
        "rss_before_bytes": rss_before,
        "rss_after_bytes": rss_after,
        "peak_rss_bytes_lower_bound": max(rss_before, rss_after),
        "io_bytes_fit_predict": None if io_before is None or io_after is None else io_after - io_before,
        "fit_rows_per_second": float(selection.realized_rows / fit_time) if fit_time > 0 else None,
        "compression_ratio": float(selection.realized_rows / len(y_train)),
        "selection_breakdown_seconds": selection.timings,
        "peak_vram_bytes": _peak_vram_bytes(),
        "passes_over_train": selection.diagnostics.get("passes_over_train"),
    }
    metrics = compute_all_metrics(
        y_eval, y_pred, y_prob, labels=labels, horizons=horizons, cost=cost
    )
    predictions = {"y_true": y_eval, "y_pred": y_pred, "y_prob": y_prob}
    return learner, metrics, predictions


def evaluate_generated(
    generated: GeneratedDatasetResult,
    y_full_train: np.ndarray,
    X_eval: np.ndarray,
    y_eval: np.ndarray,
    *,
    learner_id: str,
    model_seed: int = 42,
    learner_params: dict[str, Any] | None = None,
    X_inner_val: np.ndarray | None = None,
    y_inner_val: np.ndarray | None = None,
    horizons: np.ndarray | None = None,
    max_threads: int = 4,
) -> tuple[Any, dict[str, Any], dict[str, np.ndarray]]:
    """Train learner trên bảng synthetic nhưng dùng class-weight từ full train."""
    if generated.status != "success":
        raise RuntimeError(f"Không thể train từ generated status={generated.status}")
    class_weights = balanced_class_weights(np.asarray(y_full_train))
    sample_weight = effective_sample_weights(generated.y, generated.weights, class_weights)
    labels = np.unique(y_full_train)
    learner = build_learner(
        learner_id, seed=model_seed, input_dim=generated.X.shape[1],
        n_classes=len(labels), params=learner_params, max_threads=max_threads,
    )
    process = psutil.Process()
    cpu_before = sum(process.cpu_times()[:2])
    rss_before = process.memory_info().rss
    io_before = _io_bytes(process)
    fit_started = time.perf_counter()
    if learner_id == "mlp":
        eval_set = None if X_inner_val is None else (X_inner_val, y_inner_val)
        learner.fit(generated.X, generated.y, sample_weight=sample_weight, eval_set=eval_set)
    else:
        learner.fit(generated.X, generated.y, sample_weight=sample_weight)
    fit_time = time.perf_counter() - fit_started
    predict_started = time.perf_counter()
    y_pred = learner.predict(X_eval)
    y_prob = learner.predict_proba(X_eval) if hasattr(learner, "predict_proba") else None
    predict_time = time.perf_counter() - predict_started
    cpu_after = sum(process.cpu_times()[:2])
    rss_after = process.memory_info().rss
    io_after = _io_bytes(process)
    metrics = compute_all_metrics(
        y_eval, y_pred, y_prob, labels=labels, horizons=horizons,
        cost={
            "selection_seconds": generated.timings.get("total"),
            "fit_seconds": fit_time, "predict_seconds": predict_time,
            "realized_rows": generated.realized_rows,
            "requested_rows": generated.requested_rows,
            "total_seconds": (generated.timings.get("total") or 0.0) + fit_time + predict_time,
            "cpu_seconds_fit_predict": cpu_after - cpu_before,
            "rss_before_bytes": rss_before,
            "rss_after_bytes": rss_after,
            "peak_rss_bytes_lower_bound": max(rss_before, rss_after),
            "io_bytes_fit_predict": None if io_before is None or io_after is None else io_after - io_before,
            "fit_rows_per_second": float(generated.realized_rows / fit_time) if fit_time > 0 else None,
            "compression_ratio": float(generated.realized_rows / len(y_full_train)),
            "selection_breakdown_seconds": generated.timings,
            "peak_vram_bytes": _peak_vram_bytes(),
            "passes_over_train": generated.diagnostics.get("passes_over_train"),
        },
    )
    return learner, metrics, {"y_true": y_eval, "y_pred": y_pred, "y_prob": y_prob}


def _io_bytes(process: psutil.Process) -> int | None:
    try:
        counters = process.io_counters()
        return int(counters.read_bytes + counters.write_bytes)
    except (AttributeError, psutil.Error):
        return None


def _peak_vram_bytes() -> int | None:
    try:
        import torch
        return int(torch.cuda.max_memory_allocated()) if torch.cuda.is_available() else 0
    except ImportError:
        return None

