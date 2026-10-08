"""File này gọi trực tiếp KIP hoặc MTT từ repo TDBench đã khóa commit.

Adapter không sao chép thuật toán. Nó nạp hàm của repo tác giả, đổi budget tổng
sang số mẫu trên mỗi lớp theo contract TDBench và trả dữ liệu sinh cùng thông tin
commit. Thiếu dependency sẽ thành BLOCKED có lý do, không đổi sang thuật toán khác.
"""

from __future__ import annotations

import importlib
import importlib.util
import subprocess
import sys
import time
import types
from pathlib import Path
from typing import Any

import numpy as np

from ..contracts import exact_budget_size
from .result import GeneratedDatasetResult


class TDBenchGenerator:
    def __init__(self, method_id: str, repo_root: Path, seed: int, options: dict[str, Any] | None = None):
        self.method_id = method_id
        self.repo_root = Path(repo_root)
        self.seed = int(seed)
        self.options = dict(options or {})

    def generate(self, X_train: np.ndarray, y_train: np.ndarray, budget_ratio: float, **kwargs):
        requested = exact_budget_size(len(y_train), budget_ratio)
        repo = self.repo_root / "tdbench"
        if not (repo / "tabdd" / "distill").exists():
            return GeneratedDatasetResult.failure(
                self.method_id, "blocked", requested, f"Thiếu repo TDBench: {repo}"
            )
        commit = _git_commit(repo)
        max_rows = int(self.options.get("max_rows", 500))
        if requested > max_rows:
            return GeneratedDatasetResult.failure(
                self.method_id, "predicted_timeout", requested,
                f"Synthetic budget {requested} vượt resource gate {max_rows}; "
                "tăng method_options.max_rows chỉ sau smoke GPU",
            )
        labels = np.unique(y_train)
        per_label = requested // len(labels)
        if per_label < 1:
            return GeneratedDatasetResult.failure(
                self.method_id, "budget_infeasible", requested,
                "Budget tổng nhỏ hơn số lớp theo contract n/L của TDBench",
            )
        started = time.perf_counter()
        try:
            if self.method_id == "s_kip_tdbench":
                module = _load_distill_module(repo, "kip")
                X_syn, y_syn = module.kip(
                    np.asarray(X_train), np.asarray(y_train), per_label,
                    n_epochs=int(self.options.get("n_epochs", 100)),
                    mlp_dim=int(self.options.get("mlp_dim", 128)),
                    random_state=self.seed,
                )
            elif self.method_id == "s_mtt_tdbench":
                module = _load_distill_module(repo, "trajectory_matching")
                X_syn, y_syn = module.trajectory_matching(
                    np.asarray(X_train), np.asarray(y_train), per_label,
                    n_epochs=int(self.options.get("n_epochs", 20)),
                    n_experts=int(self.options.get("n_experts", 2)),
                    expert_epochs=int(self.options.get("expert_epochs", 2)),
                    syn_steps=int(self.options.get("syn_steps", 5)),
                    max_start_epoch=int(self.options.get("max_start_epoch", 10)),
                    mlp_dim=int(self.options.get("mlp_dim", 64)),
                    n_iter=int(self.options.get("n_iter", 100)),
                    lr_teacher=float(self.options.get("lr_teacher", 0.01)),
                    lr_data=float(self.options.get("lr_data", 0.1)),
                    lr_lr=float(self.options.get("lr_lr", 1e-5)),
                    mom_lr=float(self.options.get("mom_lr", 0.5)),
                    mom_data=float(self.options.get("mom_data", 0.5)),
                    n_hidden_layers=int(self.options.get("n_hidden_layers", 2)),
                    random_state=self.seed,
                )
            else:
                raise KeyError(self.method_id)
        except (ModuleNotFoundError, ImportError) as error:
            return GeneratedDatasetResult.failure(
                self.method_id, "blocked", requested,
                f"Dependency TDBench chưa đủ: {error}",
            )
        except Exception as error:
            return GeneratedDatasetResult.failure(
                self.method_id, "failed", requested,
                f"TDBench trả lỗi, không dùng fallback: {error!r}",
            )
        X_syn = np.asarray(X_syn, dtype=np.float32)
        y_syn = np.asarray(y_syn, dtype=np.int64)
        return GeneratedDatasetResult(
            X=X_syn,
            y=y_syn,
            weights=np.ones(len(y_syn), dtype=np.float64),
            requested_rows=requested,
            realized_rows=len(y_syn),
            generator_id=self.method_id,
            diagnostics={
                "upstream_repo": "https://github.com/inwonakng/tdbench.git",
                "upstream_commit": commit,
                "budget_contract": "TDBench n/L; realized = floor(requested/classes)*classes",
                "n_per_label": int(per_label),
                "class_counts": {str(int(v)): int(np.sum(y_syn == v)) for v in np.unique(y_syn)},
                "storage_bytes_float32": int(X_syn.astype(np.float32).nbytes + y_syn.nbytes),
            },
            timings={"generate": time.perf_counter() - started, "total": time.perf_counter() - started},
        )


def _git_commit(repo: Path) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return None


def _load_distill_module(repo: Path, module_name: str):
    """Nạp đúng file upstream mà không chạy `distill/__init__` và các extra khác."""
    root = repo / "tabdd" / "distill"
    package_name = "_skq_tdbench_distill"
    package = sys.modules.get(package_name)
    if package is None:
        package = types.ModuleType(package_name)
        package.__path__ = [str(root)]
        sys.modules[package_name] = package
    for dependency in ("random_sample", "utils"):
        qualified = f"{package_name}.{dependency}"
        if qualified not in sys.modules:
            spec = importlib.util.spec_from_file_location(qualified, root / f"{dependency}.py")
            loaded = importlib.util.module_from_spec(spec)
            sys.modules[qualified] = loaded
            assert spec.loader is not None
            spec.loader.exec_module(loaded)
    qualified = f"{package_name}.{module_name}"
    spec = importlib.util.spec_from_file_location(qualified, root / f"{module_name}.py")
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[qualified] = loaded
    assert spec.loader is not None
    spec.loader.exec_module(loaded)
    return loaded
