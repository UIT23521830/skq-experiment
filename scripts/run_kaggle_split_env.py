"""Chạy panel và KIP nối tiếp trong một Kaggle Save & Run.

Panel chính chạy trước với nguyên config nhưng loại KIP. Sau khi process
đó kết thúc, script đồng bộ toàn bộ JAX/CUDA plugin về 0.4.38 và gọi
KIP trong process Python mới. Hai pha dùng cùng config, artifact root và
experiment_id nên runner tự gộp ledger theo run_id; protocol hash không bị
đổi do tạo config rút gọn.

Script luôn aggregate và đóng gói artifact sau cùng, kể cả khi một method
ghi trạng thái failure. Trạng thái thật nằm trong ledger và
``kaggle_execution_summary.json``; không thay method bằng fallback.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import subprocess
import sys
import tarfile
import time
from collections import Counter
from pathlib import Path
from typing import Sequence

from skq_exp.config import ExperimentConfig


KIP_DISTRIBUTIONS = (
    "jax==0.4.38",
    "jaxlib==0.4.38",
    "jax-cuda12-plugin[with-cuda]==0.4.38",
    "jax-cuda12-pjrt==0.4.38",
    "neural-tangents==0.6.5",
)
KIP_UNINSTALL = (
    "jax",
    "jaxlib",
    "jax-cuda12-plugin",
    "jax-cuda12-pjrt",
)


def _run(command: Sequence[str], *, env: dict[str, str] | None = None) -> int:
    print("\n$ " + " ".join(command), flush=True)
    completed = subprocess.run(list(command), env=env, check=False)
    return int(completed.returncode)


def _capture(command: Sequence[str], *, env: dict[str, str] | None = None) -> dict:
    completed = subprocess.run(
        list(command), env=env, check=False, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    return {
        "return_code": int(completed.returncode),
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _run_command(args: argparse.Namespace, *extra: str) -> list[str]:
    command = [
        sys.executable, "-m", "skq_exp.cli", "run",
        "--config", str(Path(args.config).resolve()),
    ]
    if args.dataset:
        command.extend(["--dataset", args.dataset])
    command.extend(extra)
    for flag, value in (
        ("--max-ram-gb", args.max_ram_gb),
        ("--timeout-seconds", args.timeout_seconds),
        ("--max-threads", args.max_threads),
        ("--max-estimated-operations", args.max_estimated_operations),
    ):
        if value is not None:
            command.extend([flag, str(value)])
    return command


def _freeze() -> str:
    completed = subprocess.run(
        [sys.executable, "-m", "pip", "freeze"],
        check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    return completed.stdout


def _git_commit() -> str | None:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"], check=False, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    )
    return completed.stdout.strip() or None


def _distribution_versions() -> dict[str, str | None]:
    names = (
        "jax", "jaxlib", "jax-cuda12-plugin", "jax-cuda12-pjrt",
        "neural-tangents",
    )
    result: dict[str, str | None] = {}
    for name in names:
        try:
            result[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result[name] = None
    return result


def _verify_kip_environment(env: dict[str, str]) -> dict:
    code = (
        "import json, jax, neural_tangents; "
        "print(json.dumps({'jax': jax.__version__, "
        "'devices': [str(v) for v in jax.devices()], "
        "'default_backend': jax.default_backend()}))"
    )
    return _capture([sys.executable, "-c", code], env=env)


def _summarize_ledger(ledger_path: Path) -> dict:
    if not ledger_path.exists():
        return {"exists": False, "rows": 0, "status_counts": {}, "method_status_counts": {}}
    rows = json.loads(ledger_path.read_text(encoding="utf-8"))
    status_counts = Counter(str(row.get("status", "missing")) for row in rows)
    method_status = Counter(
        f"{row.get('method_id', 'missing')}::{row.get('status', 'missing')}"
        for row in rows
    )
    return {
        "exists": True,
        "rows": len(rows),
        "status_counts": dict(sorted(status_counts.items())),
        "method_status_counts": dict(sorted(method_status.items())),
        "kip_rows": [
            {
                key: row.get(key)
                for key in (
                    "run_id", "learner_id", "status", "macro_f1", "mcc", "reason",
                )
            }
            for row in rows if row.get("method_id") == "s_kip_tdbench"
        ],
    }


def _package(artifact_root: Path, archive_path: Path) -> None:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, "w:gz") as handle:
        handle.add(artifact_root, arcname=artifact_root.name)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--archive", required=True)
    parser.add_argument("--dataset")
    parser.add_argument("--max-ram-gb", type=float, default=12.0)
    parser.add_argument("--timeout-seconds", type=float, default=7200.0)
    parser.add_argument("--max-threads", type=int, default=4)
    parser.add_argument("--max-estimated-operations", type=float, default=50_000_000_000)
    parser.add_argument(
        "--skip-kip-install", action="store_true",
        help="Chỉ dùng khi môi trường KIP đã được pin đúng từ trước.",
    )
    args = parser.parse_args()

    config = ExperimentConfig.from_json(args.config)
    artifact_root = Path(args.artifact_root).resolve()
    configured_root = config.paths.artifact_root.resolve()
    if artifact_root != configured_root:
        raise ValueError(
            f"--artifact-root phải khớp config: {artifact_root} != {configured_root}"
        )
    artifact_root.mkdir(parents=True, exist_ok=True)
    started = time.time()
    (artifact_root / "environment_panel.txt").write_text(_freeze(), encoding="utf-8")

    # Pha 1 giữ nguyên config để protocol hash của các method và KIP giống nhau.
    panel_rc = _run(_run_command(args, "--exclude-method", "s_kip_tdbench"))

    kip_env = dict(os.environ)
    kip_env["XLA_PYTHON_CLIENT_PREALLOCATE"] = "false"
    kip_env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    uninstall_rc = None
    install_rc = None
    if panel_rc == 0 and not args.skip_kip_install:
        uninstall_rc = _run(
            [sys.executable, "-m", "pip", "uninstall", "-y", *KIP_UNINSTALL],
            env=kip_env,
        )
        install_rc = _run(
            [
                sys.executable, "-m", "pip", "install", "--no-cache-dir",
                *KIP_DISTRIBUTIONS,
            ],
            env=kip_env,
        )

    verification = _verify_kip_environment(kip_env) if panel_rc == 0 else {
        "return_code": None,
        "stdout": "",
        "stderr": "Bỏ qua vì pha panel lỗi.",
    }
    (artifact_root / "environment_kip.txt").write_text(_freeze(), encoding="utf-8")

    # Dù verify lỗi, vẫn gọi runner để failure KIP được ghi đúng vào ledger.
    kip_rc = None
    if panel_rc == 0:
        kip_rc = _run(
            _run_command(args, "--method", "s_kip_tdbench"), env=kip_env,
        )

    aggregate_rc = _run([
        sys.executable, "-m", "skq_exp.cli", "aggregate",
        "--artifact-root", str(artifact_root),
    ])
    ledger_path = artifact_root / config.experiment_id / "run_ledger.json"
    ledger_summary = _summarize_ledger(ledger_path)
    kip_success = bool(ledger_summary.get("kip_rows")) and all(
        row.get("status") == "success" for row in ledger_summary["kip_rows"]
    )
    summary = {
        "repository_commit": _git_commit(),
        "config": str(Path(args.config).resolve()),
        "experiment_id": config.experiment_id,
        "dataset": args.dataset or list(config.dataset_ids),
        "strategy": "panel_without_kip_then_pinned_kip_same_config_and_artifact_root",
        "panel_return_code": panel_rc,
        "kip_uninstall_return_code": uninstall_rc,
        "kip_install_return_code": install_rc,
        "kip_verification": verification,
        "kip_distribution_versions": _distribution_versions(),
        "kip_run_return_code": kip_rc,
        "aggregate_return_code": aggregate_rc,
        "kip_all_learners_success": kip_success,
        "ledger": ledger_summary,
        "elapsed_seconds": time.time() - started,
    }
    (artifact_root / "kaggle_execution_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8",
    )
    archive_path = Path(args.archive).resolve()
    _package(artifact_root, archive_path)
    print(json.dumps(summary, indent=2, ensure_ascii=False), flush=True)
    print(f"\nĐã đóng gói: {archive_path}", flush=True)

    # Archive luôn được tạo; exit code khác 0 giúp Kaggle hiển thị rõ pha lỗi.
    return 0 if panel_rc == 0 and kip_rc == 0 and aggregate_rc == 0 and kip_success else 2


if __name__ == "__main__":
    raise SystemExit(main())
