"""File này điều phối toàn bộ ma trận selector/generator → learner → metric.

Các method chạy theo thứ tự trong config để native structure có thể cấp cho
proposed và selection thắng có thể cấp cho D05. Dev được dùng ở screening; test
chỉ mở ở confirmatory có freeze manifest. Mọi BLOCKED/OOM/TIMEOUT vẫn vào ledger.
"""

from __future__ import annotations

import csv
import json
import platform
import time
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from .. import __version__
from ..artifacts import (
    ArtifactLayout,
    ArtifactStorageError,
    atomic_json,
    sha256_file,
    stable_hash,
)
from ..config import ExperimentConfig
from ..data import load_processed
from ..data.toy import make_toy_data
from ..methods import build_generator, build_selector, get_method_spec
from ..methods.diagnostics import equal_group_weights
from ..methods.proposed.allocation import make_group_ids
from ..methods.proposed.query_losses import make_oof_query_losses
from ..methods.result import SelectionResult
from ..methods.synthetic.result import GeneratedDatasetResult
from ..resources import ResourceGuard, ResourceLimitError, enforce_preflight, estimate_selection_cost
from ..training import evaluate_generated, evaluate_selection


def run_smoke(config: ExperimentConfig) -> list[dict[str, Any]]:
    data = make_toy_data(config.split_seed)
    rows = []
    for method_id in config.method_ids:
        spec = get_method_spec(method_id)
        if spec.output_kind != "selection" or spec.status != "implemented":
            continue
        selector = build_selector(method_id, config.selector_seeds[0], n_components=128)
        kwargs = {"parent_ids": data["parent_train"]} if spec.needs_parent else {}
        selection = selector.select(
            data["X_train"], data["y_train"], config.budget_ratio,
            row_ids=data["row_ids_train"], **kwargs,
        )
        _model, metrics, _predictions = evaluate_selection(
            selection, data["X_train"], data["y_train"], data["X_dev"], data["y_dev"],
            learner_id="lr", model_seed=config.model_seed,
        )
        rows.append({
            "method_id": method_id, "status": selection.status,
            "realized_rows": selection.realized_rows,
            "macro_f1": metrics["overall"]["f1_macro"], "mcc": metrics["overall"]["mcc"],
        })
    output = config.paths.artifact_root / "smoke" / config.experiment_id
    atomic_json(output / "smoke_results.json", rows)
    return rows


def run_config(
    config: ExperimentConfig,
    *,
    dataset_id: str | None = None,
    method_id: str | None = None,
    learner_id: str | None = None,
    resume: bool = False,
    reuse_method_artifacts: bool = False,
) -> list[dict[str, Any]]:
    if config.stage_id == "s0_smoke":
        return run_smoke(config)
    datasets = [dataset_id] if dataset_id else list(config.dataset_ids)
    methods = [method_id] if method_id else list(config.method_ids)
    learners = [learner_id] if learner_id else list(config.learner_ids)
    if config.stage_id == "s2_confirm":
        freeze = config.paths.artifact_root / "freeze" / "freeze_manifest.json"
        if not freeze.exists():
            raise RuntimeError(f"Chưa có freeze manifest: {freeze}")
    ledger: list[dict[str, Any]] = []
    layout = ArtifactLayout(config.paths.artifact_root)
    for current_dataset in datasets:
        data = load_processed(current_dataset, config.paths.processed_root)
        data_fingerprint = _dataset_fingerprint(config, current_dataset)
        eval_name = "test" if config.stage_id == "s2_confirm" else "dev"
        selection_cache: dict[tuple[str, int], SelectionResult] = {}
        structure_cache: dict[tuple[str, int], dict[str, np.ndarray]] = {}
        query_cache: dict[tuple[tuple[str, ...], int], tuple[np.ndarray, dict]] = {}
        for current_method in methods:
            seeds = [0] if current_method == "c00_full_train" else list(config.selector_seeds)
            for selector_seed in seeds:
                artifact_identity = _method_artifact_identity(
                    config, current_dataset, current_method, selector_seed, data_fingerprint,
                )
                method_artifact_dir = layout.method_artifact_dir(
                    config.experiment_id, config.protocol_id, config.stage_id,
                    current_dataset, current_method, config.budget_ratio, selector_seed,
                )
                result = None
                if reuse_method_artifacts and current_method != "c00_full_train":
                    result = layout.load_method_artifact(
                        method_artifact_dir, expected_identity=artifact_identity,
                    )
                if result is None:
                    result = _produce_or_block(
                        current_method, selector_seed, config, data, current_dataset,
                        selection_cache, structure_cache, query_cache,
                    )
                if result.status == "success":
                    _attach_generic_artifact_diagnostics(result, np.asarray(data["y_train"]))
                if isinstance(result, SelectionResult) and result.status == "success":
                    selection_cache[(current_method, selector_seed)] = result
                artifact_ref = None
                if result.status == "success" and current_method != "c00_full_train":
                    try:
                        _enforce_storage(config, layout, reserve_bytes=_result_nbytes(result))
                        artifact_ref = layout.save_method_artifact(
                            method_artifact_dir, result, artifact_identity,
                        )
                    except ArtifactStorageError as error:
                        result = _failure_like(
                            result, current_method, "storage_limit", str(error),
                        )
                for current_learner in learners:
                    manifest = _manifest(
                        config, current_dataset, current_method, current_learner,
                        selector_seed, eval_name, data_fingerprint,
                    )
                    run_dir = layout.run_dir(
                        config.experiment_id, config.protocol_id, config.stage_id,
                        current_dataset, current_method, config.budget_ratio,
                        selector_seed, current_learner, config.model_seed,
                    )
                    if resume:
                        completed = _load_completed_run(run_dir, manifest)
                        if completed is not None:
                            ledger.append(completed)
                            continue
                    allowed = get_method_spec(current_method).allowed_learners
                    if allowed is not None and current_learner not in allowed:
                        blocked = _failure_like(result, current_method, "na_contract", f"Protocol chỉ cho {current_method} chạy với {allowed}")
                        _save_failure_manifest(run_dir, manifest, blocked)
                        ledger.append({**manifest, "status": "na_contract", "reason": blocked.diagnostics["reason"]})
                        continue
                    if result.status != "success":
                        _save_failure_manifest(run_dir, manifest, result)
                        ledger.append({**manifest, "status": result.status, "reason": result.diagnostics.get("reason")})
                        continue
                    if current_method == "c00_full_train":
                        layout.save_full_reference(run_dir, result, manifest)
                    else:
                        if artifact_ref is None:
                            raise RuntimeError("Method thành công nhưng thiếu canonical artifact reference")
                        layout.save_run_reference(run_dir, result, manifest, artifact_ref)
                    try:
                        _enforce_storage(config, layout, reserve_bytes=2 * 1024 * 1024)
                        if isinstance(result, GeneratedDatasetResult):
                            model, metrics, predictions = evaluate_generated(
                                result, np.asarray(data["y_train"]),
                                np.asarray(data[f"X_{eval_name}"]), np.asarray(data[f"y_{eval_name}"]),
                                learner_id=current_learner, model_seed=config.model_seed,
                                X_inner_val=None, y_inner_val=None,
                                max_threads=int((config.resource or {}).get("max_threads", 4)),
                            )
                        else:
                            model, metrics, predictions = evaluate_selection(
                                result, np.asarray(data["X_train"]), np.asarray(data["y_train"]),
                                np.asarray(data[f"X_{eval_name}"]), np.asarray(data[f"y_{eval_name}"]),
                                learner_id=current_learner, model_seed=config.model_seed,
                                X_inner_val=None, y_inner_val=None,
                                max_threads=int((config.resource or {}).get("max_threads", 4)),
                            )
                        _save_evaluation(
                            run_dir, model, metrics, predictions,
                            policy=config.artifact_policy, layout=layout,
                            experiment_id=config.experiment_id,
                            reusable_artifact_bytes=int((artifact_ref or {}).get("artifact_bytes", 0)),
                        )
                        row = {**manifest, "status": "success", "macro_f1": metrics["overall"]["f1_macro"], "mcc": metrics["overall"]["mcc"]}
                    except ArtifactStorageError as error:
                        row = {**manifest, "status": "storage_limit", "reason": str(error)}
                        atomic_json(run_dir / "evaluation_failure.json", row)
                    except MemoryError:
                        row = {**manifest, "status": "oom"}
                        atomic_json(run_dir / "evaluation_failure.json", row)
                    except Exception as error:
                        row = {**manifest, "status": "failed", "reason": repr(error)}
                        atomic_json(run_dir / "evaluation_failure.json", row)
                    ledger.append(row)
    ledger_path = config.paths.artifact_root / config.experiment_id / "run_ledger.json"
    existing = []
    if ledger_path.exists():
        try:
            existing = json.loads(ledger_path.read_text(encoding="utf-8"))
        except Exception:
            existing = []
    merged = {row.get("run_id", stable_hash(row)[:20]): row for row in existing}
    merged.update({row.get("run_id", stable_hash(row)[:20]): row for row in ledger})
    atomic_json(ledger_path, list(merged.values()))
    return ledger


def _produce_or_block(method_id, seed, config, data, dataset_id, selection_cache, structure_cache, query_cache):
    y_train = np.asarray(data["y_train"])
    X_train = np.asarray(data["X_train"])
    requested = max(1, int(round(len(y_train) * config.budget_ratio)))
    if method_id == "c00_full_train":
        indices = np.arange(len(y_train), dtype=np.int64)
        return SelectionResult(indices, np.ones(len(indices)), len(indices), len(indices), "full", method_id)
    options = dict((config.method_options or {}).get(method_id, {}))
    if method_id == "n_autocoreset_native":
        processed = config.paths.processed_root / dataset_id
        fingerprint = stable_hash({
            "X_train": sha256_file(processed / "X_train.npy"),
            "y_train": sha256_file(processed / "y_train.npy"),
        })
        options.setdefault("dataset_fingerprint", fingerprint)
        options.setdefault(
            "native_artifact_dir",
            str(config.paths.artifact_root / "native" / "autocoreset" / dataset_id / f"ss{seed}"),
        )
    spec = get_method_spec(method_id)
    estimate = estimate_selection_cost(method_id, len(y_train), X_train.shape[1], requested, n_classes=len(np.unique(y_train)))
    try:
        enforce_preflight(estimate, config.resource)
    except ResourceLimitError as error:
        return _failure_for_kind(spec.output_kind, method_id, error.status, requested, str(error))
    guard = ResourceGuard(config.resource)
    if spec.output_kind == "synthetic":
        try:
            generator = build_generator(method_id, seed, external_root=config.paths.external_root, options=options)
            return generator.generate(X_train, y_train, config.budget_ratio, resource_guard=guard)
        except Exception as error:
            return GeneratedDatasetResult.failure(method_id, "failed", requested, repr(error))
    if method_id == "d05_equal_group_weight":
        source = str(options.get("source_method", "p05_skq_lrq_mq"))
        base = selection_cache.get((source, seed))
        if base is None:
            base = _load_selection_artifact(config, dataset_id, source, seed)
        if base is None:
            return SelectionResult.failure(method_id, "blocked", requested, f"D05 cần source selection chạy trước: {source}")
        parent_result = _resolve_structure(options, seed, structure_cache, config, dataset_id)
        if isinstance(parent_result, str):
            return SelectionResult.failure(method_id, "blocked", requested, parent_result)
        group_ids = make_group_ids(parent_result.get("parent_ids"), y_train)
        return equal_group_weights(base, group_ids)
    try:
        selector = build_selector(
            method_id, seed, external_root=config.paths.external_root,
            options=options, n_components=int(options.get("n_components", 256)),
        )
    except (KeyError, RuntimeError) as error:
        return SelectionResult.failure(method_id, "blocked", requested, str(error))
    kwargs: dict[str, Any] = {"row_ids": np.asarray(data["row_ids_train"]), "resource_guard": guard}
    structure = None
    if spec.needs_parent:
        structure = _resolve_structure(options, seed, structure_cache, config, dataset_id)
        if isinstance(structure, str):
            return SelectionResult.failure(method_id, "blocked", requested, structure)
        kwargs["parent_ids"] = structure["parent_ids"]
        if method_id == "p03_skq_bdis_filtered":
            if "candidate_mask" not in structure:
                return SelectionResult.failure(method_id, "blocked", requested, "BDIS structure thiếu candidate_mask")
            kwargs["candidate_mask"] = structure["candidate_mask"]
    if method_id in {"p04_skq_lrq_sq", "p05_skq_lrq_mq"}:
        query_ids = tuple(options.get("query_learners", ["lr"] if method_id.endswith("sq") else ["lr", "rf", "xgb"]))
        cache_key = (query_ids, seed)
        if cache_key not in query_cache:
            try:
                query_started = time.perf_counter()
                query_values, query_metadata = make_oof_query_losses(
                    X_train, y_train, query_ids, seed=seed,
                    folds=int(options.get("oof_folds", 5)),
                    max_threads=int((config.resource or {}).get("max_threads", 4)),
                )
                query_metadata["seconds"] = time.perf_counter() - query_started
                query_cache[cache_key] = (query_values, query_metadata)
            except Exception as error:
                return SelectionResult.failure(method_id, "failed", requested, f"OOF query loss lỗi: {error!r}")
        kwargs["query_features"], kwargs["query_metadata"] = query_cache[cache_key]
    try:
        result = selector.select(X_train, y_train, config.budget_ratio, **kwargs)
    except ResourceLimitError as error:
        return SelectionResult.failure(method_id, error.status, requested, str(error))
    if result.status == "success" and spec.needs_parent:
        own_total = float(result.timings.get("total", 0.0))
        parent_total = float(np.asarray(structure.get("_producer_total_seconds", 0.0)).item())
        query_total = float((kwargs.get("query_metadata") or {}).get("seconds", 0.0))
        result.timings["skq_only"] = own_total
        result.timings["parent_structure"] = parent_total
        result.timings["query"] = query_total
        result.timings["total"] = own_total + parent_total + query_total
    if getattr(selector, "structure_parent_ids_", None) is not None:
        structure = {
            "parent_ids": np.asarray(selector.structure_parent_ids_, dtype=np.int64),
            "_producer_total_seconds": np.asarray(result.timings.get("total", 0.0), dtype=np.float64),
        }
        if getattr(selector, "candidate_mask_", None) is not None:
            structure["candidate_mask"] = np.asarray(selector.candidate_mask_, dtype=bool)
        structure_cache[(method_id, seed)] = structure
        _save_structure(config, dataset_id, method_id, seed, structure, result)
    return result


def _resolve_structure(options, seed, structure_cache, config, dataset_id):
    source = options.get("parent_source")
    if not source:
        return "Thiếu method_options.parent_source; runner không tự đoán structure winner"
    structure = structure_cache.get((str(source), seed))
    if structure is None:
        path = (
            config.paths.artifact_root / "structures" / config.experiment_id /
            dataset_id / str(source) / f"ss{seed}" / "structure.npz"
        )
        if path.exists():
            with np.load(path) as saved:
                structure = {key: saved[key] for key in saved.files}
            structure_cache[(str(source), seed)] = structure
        else:
            return f"Structure source chưa chạy thành công trước method này: {source}, seed={seed}"
    return structure


def _save_structure(config, dataset_id, method_id, seed, structure, result):
    root = config.paths.artifact_root / "structures" / config.experiment_id / dataset_id / method_id / f"ss{seed}"
    root.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(root / "structure.npz", **structure)
    atomic_json(root / "structure.json", {
        "producer_method": method_id, "selector_seed": seed,
        "n_rows": int(len(structure["parent_ids"])),
        "n_groups": int(len(np.unique(structure["parent_ids"]))),
        "selection_status": result.status,
        "diagnostics": result.diagnostics,
    })


def _load_selection_artifact(config, dataset_id, method_id, seed):
    """Nạp selection có sẵn để D05 chạy riêng mà không rerun source selector."""
    canonical_root = (
        config.paths.artifact_root / "method_artifacts" / config.experiment_id /
        config.protocol_id / config.stage_id / dataset_id / method_id
    )
    canonical = sorted(canonical_root.rglob("selected_indices.npy")) if canonical_root.exists() else []
    canonical = [path for path in canonical if f"ss{seed}" in path.parts]
    if canonical:
        selected_path = canonical[0]
        artifact_dir = selected_path.parent
        try:
            stored = json.loads(
                (artifact_dir / "artifact_manifest.json").read_text(encoding="utf-8")
            )["result"]
            return SelectionResult(
                indices=np.load(selected_path),
                weights=np.load(artifact_dir / "sample_weights.npy"),
                requested_rows=int(stored["requested_rows"]),
                realized_rows=int(stored["realized_rows"]),
                budget_mode=str(stored["budget_mode"]),
                method_id=method_id,
                diagnostics={"loaded_from": str(artifact_dir)},
                timings=stored.get("timings", {}),
            )
        except (OSError, KeyError, ValueError, TypeError):
            pass
    # Tương thích artifact cũ trước khi canonical store được đưa vào.
    root = (
        config.paths.artifact_root / "experiments" / config.experiment_id /
        config.protocol_id / config.stage_id / dataset_id / method_id
    )
    candidates = sorted(root.rglob("selected_indices.npy")) if root.exists() else []
    candidates = [path for path in candidates if f"ss{seed}" in path.parts]
    if not candidates:
        return None
    selected_path = candidates[0]
    run_dir = selected_path.parent
    try:
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        return SelectionResult(
            indices=np.load(selected_path),
            weights=np.load(run_dir / "sample_weights.npy"),
            requested_rows=int(manifest["requested_rows"]),
            realized_rows=int(manifest["realized_rows"]),
            budget_mode=str(manifest["budget_mode"]),
            method_id=method_id,
            diagnostics={"loaded_from": str(run_dir)},
            timings=manifest.get("timings", {}),
        )
    except Exception:
        return None


def _failure_for_kind(kind, method_id, status, requested, reason):
    if kind == "synthetic":
        return GeneratedDatasetResult.failure(method_id, status, requested, reason)
    return SelectionResult.failure(method_id, status, requested, reason)


def _failure_like(result, method_id, status, reason):
    return _failure_for_kind("synthetic" if isinstance(result, GeneratedDatasetResult) else "selection", method_id, status, result.requested_rows, reason)


def _save_failure_manifest(run_dir, manifest, result):
    run_dir.mkdir(parents=True, exist_ok=True)
    atomic_json(run_dir / "manifest.json", {**manifest, **result.to_dict()})


def _manifest(
    config, dataset_id, method_id, learner_id, selector_seed, eval_name,
    data_fingerprint,
):
    identity = {
        "experiment_id": config.experiment_id, "protocol_id": config.protocol_id,
        "stage_id": config.stage_id, "dataset_id": dataset_id, "method_id": method_id,
        "budget_ratio": config.budget_ratio, "selector_seed": selector_seed,
        "learner_id": learner_id, "model_seed": config.model_seed,
        "evaluation_split": eval_name, "data_fingerprint": data_fingerprint,
        "protocol_hash": _protocol_hash(config),
    }
    return {**identity, "run_id": stable_hash(identity)[:20], "package_version": __version__, "python": platform.python_version(), "created_unix": time.time()}


def _save_evaluation(
    run_dir: Path,
    model,
    metrics,
    predictions,
    policy=None,
    *,
    layout: ArtifactLayout,
    experiment_id: str,
    reusable_artifact_bytes: int = 0,
) -> None:
    policy = policy or {}
    retention = {
        "model": "not_requested",
        "predictions": "not_requested",
        "probabilities": "not_requested",
        "y_true": "not_requested",
    }
    if bool(policy.get("save_models", False)):
        try:
            _enforce_storage_policy(
                policy, layout, experiment_id,
                reserve_bytes=int(policy.get("model_reserve_mb", 128) * 1024 ** 2),
            )
            joblib.dump(model, run_dir / "model.joblib", compress=3)
            retention["model"] = "saved"
        except ArtifactStorageError as error:
            retention["model"] = f"skipped_storage_guard: {error}"
    if bool(policy.get("save_predictions", False)):
        payload = {"y_pred": np.asarray(predictions["y_pred"])}
        if bool(policy.get("save_y_true", False)):
            payload["y_true"] = np.asarray(predictions["y_true"])
        if bool(policy.get("save_probabilities", False)) and predictions.get("y_prob") is not None:
            probability_dtype = str(policy.get("probability_dtype", "float32"))
            if probability_dtype not in {"float16", "float32", "float64"}:
                raise ValueError("artifact_policy.probability_dtype không hợp lệ")
            payload["y_prob"] = np.asarray(predictions["y_prob"], dtype=probability_dtype)
        estimated_bytes = int(sum(value.nbytes for value in payload.values()))
        per_run_limit = int(float(policy.get("max_prediction_mb_per_run", 64)) * 1024 ** 2)
        if estimated_bytes > per_run_limit:
            retention["predictions"] = (
                f"skipped_per_run_limit: {estimated_bytes} > {per_run_limit} bytes"
            )
        else:
            try:
                _enforce_storage_policy(
                    policy, layout, experiment_id, reserve_bytes=estimated_bytes,
                )
                np.savez_compressed(run_dir / "predictions.npz", **payload)
                retention["predictions"] = "saved_y_pred"
                retention["y_true"] = "saved" if "y_true" in payload else "reload_from_processed_split"
                retention["probabilities"] = "saved" if "y_prob" in payload else "metrics_only"
            except ArtifactStorageError as error:
                retention["predictions"] = f"skipped_storage_guard: {error}"
    with (run_dir / "metrics_per_label.csv").open("w", newline="", encoding="utf-8") as stream:
        rows = metrics["per_label"]
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]) if rows else [])
        if rows:
            writer.writeheader()
            writer.writerows(rows)
    np.savetxt(run_dir / "confusion_matrix.csv", np.asarray(metrics["confusion_matrix"]), delimiter=",", fmt="%d")
    cost = dict(metrics.get("cost", {}))
    evaluation_bytes = int(sum(
        path.stat().st_size for path in run_dir.rglob("*") if path.is_file()
    ))
    cost["evaluation_artifact_bytes"] = evaluation_bytes
    cost["reusable_method_artifact_bytes"] = int(reusable_artifact_bytes)
    cost["artifact_bytes_total_for_replay"] = evaluation_bytes + int(reusable_artifact_bytes)
    # Tên cũ được giữ để bảng đã viết không vỡ, nhưng giá trị nay có định nghĩa rõ hơn.
    cost["artifact_bytes_lower_bound"] = cost["artifact_bytes_total_for_replay"]
    cost.setdefault("break_even_reuses", None)
    metrics["cost"] = cost
    atomic_json(run_dir / "cost.json", cost)
    atomic_json(run_dir / "retention.json", retention)
    atomic_json(run_dir / "metrics_overall.json", metrics["overall"])
    atomic_json(run_dir / "metrics_all.json", metrics)


def _protocol_hash(config: ExperimentConfig) -> str:
    payload = config.to_dict()
    payload.pop("paths", None)
    payload.pop("resource", None)
    payload.pop("artifact_policy", None)
    return stable_hash(payload)


def _dataset_fingerprint(config: ExperimentConfig, dataset_id: str) -> str:
    manifest = config.paths.processed_root / dataset_id / "preprocessing_manifest.json"
    if not manifest.exists():
        raise FileNotFoundError(f"Thiếu preprocessing manifest: {manifest}")
    return sha256_file(manifest)


def _method_artifact_identity(
    config: ExperimentConfig,
    dataset_id: str,
    method_id: str,
    selector_seed: int,
    data_fingerprint: str,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "experiment_id": config.experiment_id,
        "protocol_id": config.protocol_id,
        "stage_id": config.stage_id,
        "dataset_id": dataset_id,
        "method_id": method_id,
        "budget_ratio": config.budget_ratio,
        "selector_seed": selector_seed,
        "split_seed": config.split_seed,
        "method_options": (config.method_options or {}).get(method_id, {}),
        "data_fingerprint": data_fingerprint,
        "protocol_hash": _protocol_hash(config),
        "package_version": __version__,
    }


def _attach_generic_artifact_diagnostics(result: Any, y_train: np.ndarray) -> None:
    n_train = int(len(y_train))
    realized = int(result.realized_rows)
    result.diagnostics.setdefault("requested_rows", int(result.requested_rows))
    result.diagnostics.setdefault("realized_rows", realized)
    result.diagnostics.setdefault("realized_fraction", realized / n_train if n_train else None)
    result.diagnostics.setdefault("compression_ratio", n_train / realized if realized else None)
    weights = np.asarray(result.weights, dtype=np.float64)
    if len(weights):
        denominator = float(len(weights) * np.sum(weights ** 2))
        result.diagnostics.setdefault(
            "normalized_ess",
            float(weights.sum() ** 2 / denominator) if denominator else None,
        )
        result.diagnostics.setdefault("zero_weight_share", float(np.mean(weights == 0)))
        result.diagnostics.setdefault("weight_sum", float(weights.sum()))
    if isinstance(result, SelectionResult):
        result.diagnostics.setdefault(
            "unique_id_ratio",
            float(len(np.unique(result.indices)) / realized) if realized else None,
        )
        selected_labels = np.unique(y_train[result.indices]) if realized else np.empty(0)
        result.diagnostics.setdefault(
            "class_coverage",
            float(len(selected_labels) / len(np.unique(y_train))) if len(y_train) else None,
        )


def _result_nbytes(result: Any) -> int:
    if isinstance(result, GeneratedDatasetResult):
        return int(result.X.nbytes + result.y.nbytes + result.weights.nbytes)
    return int(result.indices.nbytes + result.weights.nbytes)


def _enforce_storage(config: ExperimentConfig, layout: ArtifactLayout, reserve_bytes: int) -> None:
    _enforce_storage_policy(
        config.artifact_policy or {}, layout, config.experiment_id,
        reserve_bytes=reserve_bytes,
    )


def _enforce_storage_policy(
    policy: dict[str, Any],
    layout: ArtifactLayout,
    experiment_id: str,
    *,
    reserve_bytes: int,
) -> None:
    layout.enforce_storage_budget(
        experiment_id,
        max_artifact_gb=float(policy.get("max_experiment_artifact_gb", 1.0)),
        min_free_disk_gb=float(policy.get("min_free_disk_gb", 2.0)),
        reserve_bytes=reserve_bytes,
    )


def _load_completed_run(run_dir: Path, expected_manifest: dict[str, Any]) -> dict[str, Any] | None:
    manifest_path = run_dir / "manifest.json"
    metrics_path = run_dir / "metrics_overall.json"
    if not manifest_path.exists() or not metrics_path.exists():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("run_id") != expected_manifest.get("run_id"):
            return None
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        return {
            **expected_manifest,
            "status": "success",
            "macro_f1": metrics.get("f1_macro"),
            "mcc": metrics.get("mcc"),
            "resumed": True,
        }
    except (OSError, ValueError, TypeError):
        return None
