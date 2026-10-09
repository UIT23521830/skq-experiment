"""File này cung cấp các lệnh ngắn để chạy cùng một API trên local và Kaggle.

`doctor` kiểm tra môi trường, `prepare` tạo processed data, `smoke` kiểm tra luồng
nhỏ, `run` chạy stage trong config và `aggregate` gom artifact. Lệnh không chứa
thuật toán nên kết quả không phụ thuộc việc gọi từ notebook hay terminal.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import sys
from dataclasses import replace
from pathlib import Path

from .config import ExperimentConfig
from .data import fetch_dataset, prepare_course_quality_snapshot, prepare_dataset
from .experiments import run_config, run_smoke
from .methods import allowed_learners_for, get_method_spec
from .reports import aggregate_results


def main(argv: list[str] | None = None) -> int:
    # Windows terminal cũ có thể dùng cp1252; đổi sang UTF-8 để phần trợ giúp tiếng Việt đọc được.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="skq", description="SKQ experiment runner")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    plan = sub.add_parser("plan")
    plan.add_argument("--config", required=True)
    plan.add_argument("--show-cells", action="store_true")
    smoke = sub.add_parser("smoke")
    smoke.add_argument("--config", required=True)
    smoke.add_argument(
        "--selector-seed", type=int, action="append",
        help="Ghi đè selector seed; có thể lặp option để chạy nhiều seed.",
    )
    smoke.add_argument("--model-seed", type=int, help="Ghi đè seed của downstream model.")
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--config", required=True)
    prepare.add_argument("--dataset", required=True)
    prepare.add_argument("--overwrite", action="store_true")
    prepare_cq = sub.add_parser("prepare-course-quality")
    prepare_cq.add_argument("--config", required=True)
    prepare_cq.add_argument("--input-dir", required=True)
    prepare_cq.add_argument("--dataset", default="course_quality_med_v1")
    prepare_cq.add_argument("--overwrite", action="store_true")
    fetch = sub.add_parser("fetch-data")
    fetch.add_argument("--config", required=True)
    fetch.add_argument("--dataset", required=True)
    fetch.add_argument("--overwrite", action="store_true")
    run = sub.add_parser("run")
    run.add_argument("--config", required=True)
    run.add_argument("--dataset")
    run.add_argument("--method")
    run.add_argument(
        "--exclude-method", action="append", default=[],
        help=(
            "Bỏ method khỏi full run nhưng không đổi config/protocol hash; "
            "có thể lặp option."
        ),
    )
    run.add_argument("--learner")
    run.add_argument(
        "--selector-seed", type=int, action="append",
        help="Ghi đè selector seed; ví dụ --selector-seed 11. Lặp option để thêm seed.",
    )
    run.add_argument("--model-seed", type=int, help="Ghi đè seed của downstream model.")
    run.add_argument("--max-ram-gb", type=float, help="Giới hạn RSS cho selector.")
    run.add_argument("--timeout-seconds", type=float, help="Giới hạn thời gian selector.")
    run.add_argument("--max-threads", type=int, help="Số CPU thread tối đa cho learner.")
    run.add_argument(
        "--max-estimated-operations", type=float,
        help="Không khởi chạy method nếu ước lượng phép tính vượt ngưỡng này.",
    )
    run.add_argument("--save-model", action="store_true", help="Lưu fitted model; mặc định không lưu.")
    aggregate = sub.add_parser("aggregate")
    aggregate.add_argument("--artifact-root", required=True)
    args = parser.parse_args(argv)

    if args.command == "doctor":
        print(json.dumps(_doctor(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "aggregate":
        print(aggregate_results(args.artifact_root))
        return 0
    config = ExperimentConfig.from_json(args.config)
    if args.command == "plan":
        print(json.dumps(_plan(config, include_cells=args.show_cells), indent=2, ensure_ascii=False))
        return 0
    if getattr(args, "selector_seed", None):
        config = replace(config, selector_seeds=tuple(args.selector_seed))
    if getattr(args, "model_seed", None) is not None:
        config = replace(config, model_seed=int(args.model_seed))
    resource = dict(config.resource or {})
    for argument, key in [
        (getattr(args, "max_ram_gb", None), "max_ram_gb"),
        (getattr(args, "timeout_seconds", None), "timeout_seconds"),
        (getattr(args, "max_threads", None), "max_threads"),
        (getattr(args, "max_estimated_operations", None), "max_estimated_operations"),
    ]:
        if argument is not None:
            resource[key] = argument
    artifact_policy = dict(config.artifact_policy or {})
    if getattr(args, "save_model", False):
        artifact_policy["save_models"] = True
    config = replace(config, resource=resource, artifact_policy=artifact_policy)
    config.validate()
    if args.command == "smoke":
        print(json.dumps(run_smoke(config), indent=2, ensure_ascii=False))
        return 0
    if args.command == "prepare":
        print(prepare_dataset(
            args.dataset, config.paths.raw_root, config.paths.processed_root,
            overwrite=args.overwrite,
        ))
        return 0
    if args.command == "prepare-course-quality":
        print(prepare_course_quality_snapshot(
            args.input_dir, config.paths.processed_root,
            dataset_id=args.dataset, overwrite=args.overwrite,
        ))
        return 0
    if args.command == "fetch-data":
        print(fetch_dataset(args.dataset, config.paths.raw_root, overwrite=args.overwrite))
        return 0
    print(json.dumps(run_config(
        config, dataset_id=args.dataset, method_id=args.method, learner_id=args.learner,
        exclude_method_ids=tuple(getattr(args, "exclude_method", ())),
    ), indent=2, ensure_ascii=False, default=str))
    return 0


def _doctor() -> dict:
    core = ["numpy", "scipy", "pandas", "sklearn", "xgboost", "catboost", "torch", "psutil", "ahocorasick", "statsmodels"]
    optional = [
        "faiss", "fast_enum", "iterstrat", "jax", "neural_tangents", "torchvision",
    ]
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages_core": {name: importlib.util.find_spec(name) is not None for name in core},
        "packages_optional_native_synthetic": {
            name: importlib.util.find_spec(name) is not None for name in optional
        },
        "cwd": str(Path.cwd()),
    }


def _plan(config: ExperimentConfig, *, include_cells: bool = False) -> dict:
    cells = []
    for method_id in config.method_ids:
        spec = get_method_spec(method_id)
        allowed = allowed_learners_for(
            method_id, (config.method_options or {}).get(method_id),
        )
        for learner_id in config.learner_ids:
            contract = "planned"
            if allowed is not None and learner_id not in allowed:
                contract = "na_contract"
            cells.append({
                "method_id": method_id,
                "role": spec.role,
                "output_kind": spec.output_kind,
                "learner_id": learner_id,
                "contract": contract,
            })
    result = {
        "experiment_id": config.experiment_id,
        "datasets": list(config.dataset_ids),
        "selector_seeds": list(config.selector_seeds),
        "methods_total_including_fulltrain": len(config.method_ids),
        "compression_or_generation_methods": sum(method != "c00_full_train" for method in config.method_ids),
        "learners": list(config.learner_ids),
        "cells_total_per_dataset_seed": len(cells),
        "cells_planned": sum(cell["contract"] == "planned" for cell in cells),
        "cells_na_contract": sum(cell["contract"] == "na_contract" for cell in cells),
    }
    if include_cells:
        result["cells"] = cells
    return result


if __name__ == "__main__":
    raise SystemExit(main())
