"""Adapters chạy trực tiếp hai hàm selector trong repo benchmark chính thức.

Repo upstream hiện gom cả các baseline tổng hợp vào một file có import optional
SDV và thiếu import ``PCA`` ở hàm leverage. Adapter này chỉ compile đúng hai
``FunctionDef`` cần dùng từ file upstream, inject các dependency tối thiểu, rồi
không chạy phần code không liên quan. Như vậy thuật toán vẫn là code upstream,
nhưng provenance ghi rõ compatibility boundary và việc khôi phục index cho
Gonzalez vì hàm gốc chỉ trả về các dòng đã chọn.
"""

from __future__ import annotations

import ast
import time
from pathlib import Path

import numpy as np
from sklearn.decomposition import PCA

from ..base import BaseSelector
from ..contracts import exact_budget_size
from ..result import SelectionResult
from ..native.common import git_commit


def _load_upstream_functions(repo: Path) -> dict[str, object]:
    """Compile only the two upstream functions, bypassing unrelated SDV imports."""
    source_path = repo / "tabular_distillation_method.py"
    if not source_path.exists():
        raise FileNotFoundError(f"Thiếu source upstream: {source_path}")
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    wanted = {
        node.name: node for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name in {"distill_coreset", "distill_coreset_leverage_scores"}
    }
    missing = {"distill_coreset", "distill_coreset_leverage_scores"} - set(wanted)
    if missing:
        raise RuntimeError(f"Source upstream thiếu hàm: {sorted(missing)}")
    namespace = {"np": np, "PCA": PCA}
    compiled = {}
    for name, node in wanted.items():
        module = ast.Module(body=[node], type_ignores=[])
        code = compile(ast.fix_missing_locations(module), str(source_path), "exec")
        exec(code, namespace, namespace)
        compiled[name] = namespace[name]
    return compiled


def _recover_indices(X: np.ndarray, selected: np.ndarray) -> np.ndarray:
    """Recover upstream Gonzalez row positions without changing selected rows."""
    X = np.asarray(X)
    selected = np.asarray(selected)
    buckets: dict[bytes, list[int]] = {}
    for index, row in enumerate(X):
        buckets.setdefault(np.ascontiguousarray(row).tobytes(), []).append(index)
    recovered: list[int] = []
    for row in selected:
        key = np.ascontiguousarray(row).tobytes()
        candidates = buckets.get(key, [])
        if not candidates:
            raise RuntimeError("Không khôi phục được index từ output Gonzalez upstream")
        recovered.append(candidates.pop(0))
    if len(set(recovered)) != len(recovered):
        raise RuntimeError("Output Gonzalez upstream chứa dòng trùng không thể ánh xạ duy nhất")
    return np.asarray(recovered, dtype=np.int64)


class GonzalezBenchmarkSelector(BaseSelector):
    method_id = "n_gcoreset_benchmark"

    def __init__(self, repo_root: Path, seed: int):
        super().__init__(seed)
        self.repo = Path(repo_root) / "tabular_data_distillation"

    def select(self, X_train, y_train, budget_ratio, **kwargs):
        requested = exact_budget_size(len(y_train), budget_ratio)
        started = time.perf_counter()
        X = np.asarray(X_train)
        functions = _load_upstream_functions(self.repo)
        np.random.seed(self.seed)
        selected_X, _selected_y = functions["distill_coreset"](
            X, np.asarray(y_train), requested * 100 / len(X),
        )
        indices = _recover_indices(X, selected_X)
        elapsed = time.perf_counter() - started
        return SelectionResult(
            indices=np.asarray(indices), weights=np.ones(requested), requested_rows=requested,
            realized_rows=requested, budget_mode="exact_total", method_id=self.method_id,
            diagnostics={
                "upstream_repo": "https://github.com/corneliuflorea/Tabular-Data-Distillation.git",
                "upstream_commit": git_commit(self.repo),
                "fidelity": "official upstream function executed through a narrow compatibility adapter",
                "execution_mode": "upstream_source_function",
                "compatibility_patch": "seed injection and output-row-to-index recovery",
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
        functions = _load_upstream_functions(self.repo)
        np.random.seed(self.seed)
        _selected_X, _selected_y, indices = functions["distill_coreset_leverage_scores"](
            X, np.asarray(y_train), requested * 100 / len(X),
        )
        indices = np.asarray(indices, dtype=np.int64)
        elapsed = time.perf_counter() - started
        return SelectionResult(
            indices=indices, weights=np.ones(requested), requested_rows=requested,
            realized_rows=requested, budget_mode="exact_total", method_id=self.method_id,
            diagnostics={
                "upstream_repo": "https://github.com/corneliuflorea/Tabular-Data-Distillation.git",
                "upstream_commit": git_commit(self.repo),
                "fidelity": "official upstream function executed through a narrow compatibility adapter",
                "execution_mode": "upstream_source_function",
                "compatibility_patch": "injected missing sklearn PCA name and explicit seed",
                "pca_components": int(min(20, X.shape[1])),
                "upstream_function": "distill_coreset_leverage_scores",
            }, timings={"select": elapsed, "total": elapsed},
        )
