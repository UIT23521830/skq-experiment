"""File này tái hiện hai selector của Tabular Data Distillation benchmark.

Gonzalez chọn điểm xa nhất lặp lại; Leverage dùng PCA rồi lấy mẫu theo tổng bình
phương tọa độ. Code giữ công thức upstream, bổ sung seed và import PCA còn thiếu
để replay được, vì vậy provenance là benchmark-reimplementation chứ không native.
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
from sklearn.decomposition import PCA

from ..base import BaseSelector
from ..contracts import exact_budget_size
from ..result import SelectionResult
from ..native.common import git_commit


class GonzalezBenchmarkSelector(BaseSelector):
    method_id = "n_gcoreset_benchmark"

    def __init__(self, repo_root: Path, seed: int):
        super().__init__(seed)
        self.repo = Path(repo_root) / "tabular_data_distillation"

    def select(self, X_train, y_train, budget_ratio, **kwargs):
        requested = exact_budget_size(len(y_train), budget_ratio)
        started = time.perf_counter()
        first = int(self.rng.integers(0, len(X_train)))
        indices = [first]
        distances = np.full(len(X_train), np.inf)
        X = np.asarray(X_train)
        guard = kwargs.get("resource_guard")
        for step in range(requested - 1):
            distances = np.minimum(distances, np.linalg.norm(X - X[indices[-1]], axis=1))
            distances[indices] = -np.inf
            indices.append(int(np.argmax(distances)))
            if guard is not None and step % 32 == 0:
                guard.check("gonzalez_farthest_first")
        elapsed = time.perf_counter() - started
        return SelectionResult(
            indices=np.asarray(indices), weights=np.ones(requested), requested_rows=requested,
            realized_rows=requested, budget_mode="exact_total", method_id=self.method_id,
            diagnostics={
                "upstream_repo": "https://github.com/corneliuflorea/Tabular-Data-Distillation.git",
                "upstream_commit": git_commit(self.repo),
                "fidelity": "formula-equivalent benchmark reimplementation with explicit seed",
                "upstream_function": "distill_coreset",
            }, timings={"select": elapsed, "total": elapsed},
        )


class LeverageBenchmarkSelector(BaseSelector):
    method_id = "n_leverage_benchmark"

    def __init__(self, repo_root: Path, seed: int):
        super().__init__(seed)
        self.repo = Path(repo_root) / "tabular_data_distillation"

    def select(self, X_train, y_train, budget_ratio, **kwargs):
        requested = exact_budget_size(len(y_train), budget_ratio)
        started = time.perf_counter()
        X = np.asarray(X_train)
        components = min(20, X.shape[1], len(X) - 1)
        Z = PCA(n_components=components, svd_solver="auto", random_state=self.seed).fit_transform(X)
        leverage = np.sum(Z ** 2, axis=1)
        if not np.isfinite(leverage).all() or leverage.sum() <= 0:
            return SelectionResult.failure(self.method_id, "failed", requested, "Leverage probabilities không hợp lệ")
        probabilities = leverage / leverage.sum()
        indices = self.rng.choice(len(X), size=requested, replace=False, p=probabilities)
        elapsed = time.perf_counter() - started
        return SelectionResult(
            indices=indices, weights=np.ones(requested), requested_rows=requested,
            realized_rows=requested, budget_mode="exact_total", method_id=self.method_id,
            diagnostics={
                "upstream_repo": "https://github.com/corneliuflorea/Tabular-Data-Distillation.git",
                "upstream_commit": git_commit(self.repo),
                "fidelity": "formula-equivalent benchmark reimplementation",
                "compatibility_patch": "added missing sklearn PCA import and explicit seed",
                "pca_components": int(components),
            }, timings={"select": elapsed, "total": elapsed},
        )
