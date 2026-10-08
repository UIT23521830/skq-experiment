"""File này tái hiện CRAIG logistic bằng facility-location của repo tác giả.

Khoảng cách và lazy-greedy được lấy trực tiếp từ `lazy_greedy.py`. Vì phép tính
pairwise là O(n²), runner phải qua preflight RAM/operations trước khi gọi file này.
Native realized size được giữ nguyên khi quota lớp dùng phép làm tròn trần của repo.
"""

from __future__ import annotations

import importlib.util
import time
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import pairwise_distances

from ..base import BaseSelector
from ..contracts import exact_budget_size
from ..result import SelectionResult
from .common import git_commit


class CRAIGNativeSelector(BaseSelector):
    method_id = "n_craig_native"

    def __init__(self, repo_root: Path, seed: int, options: dict[str, Any] | None = None):
        super().__init__(seed)
        self.repo = Path(repo_root) / "craig"
        self.options = dict(options or {})

    def select(self, X_train, y_train, budget_ratio, **kwargs):
        requested = exact_budget_size(len(y_train), budget_ratio)
        source = self.repo / "lazy_greedy.py"
        if not source.exists():
            return SelectionResult.failure(self.method_id, "blocked", requested, f"Thiếu repo: {self.repo}")
        guard = kwargs.get("resource_guard")
        started = time.perf_counter()
        try:
            spec = importlib.util.spec_from_file_location("craig_upstream_lazy_greedy", source)
            module = importlib.util.module_from_spec(spec)
            assert spec.loader is not None
            spec.loader.exec_module(module)
            selected, weights = [], []
            labels, counts = np.unique(y_train, return_counts=True)
            quotas = np.ceil(counts / len(y_train) * requested).astype(int)
            for label, quota in zip(labels, quotas):
                pool = np.flatnonzero(np.asarray(y_train) == label)
                if guard is not None:
                    guard.check(f"craig_pairwise_class_{label}")
                distances = pairwise_distances(np.asarray(X_train)[pool], metric="euclidean", n_jobs=1)
                similarities = distances.max() - distances
                objective = module.FacilityLocation(similarities, list(range(len(pool))))
                local, _ = module.lazy_greedy_heap(objective, list(range(len(pool))), min(int(quota), len(pool)))
                local = np.asarray(local, dtype=np.int64)
                chosen = pool[local]
                selected.extend(chosen.tolist())
                assignment = np.argmax(similarities[:, local], axis=1)
                weights.extend(np.bincount(assignment, minlength=len(local)).astype(float).tolist())
                del distances, similarities
        except MemoryError:
            return SelectionResult.failure(self.method_id, "oom", requested, "CRAIG hết bộ nhớ ở ma trận pairwise")
        except Exception as error:
            return SelectionResult.failure(self.method_id, "failed", requested, f"CRAIG upstream lỗi: {error!r}")
        elapsed = time.perf_counter() - started
        indices = np.asarray(selected, dtype=np.int64)
        return SelectionResult(
            indices=indices, weights=np.asarray(weights), requested_rows=requested,
            realized_rows=len(indices), budget_mode="native_realized", method_id=self.method_id,
            diagnostics={
                "upstream_repo": "https://github.com/baharanm/craig.git",
                "upstream_commit": git_commit(self.repo),
                "reference_equivalent": True,
                "pipeline": "repo logistic feature-space classwise facility location",
                "class_quotas_ceil": quotas.tolist(),
            },
            timings={"select": elapsed, "total": elapsed},
        )
