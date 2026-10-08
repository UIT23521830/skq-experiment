"""File này nối N01/N02 với CoreTab chính thức và xuất cấu trúc lá.

Native output giữ nguyên kích thước do CoreTab tạo, không trim/pad về 5%. Sau khi
chạy, `structure_parent_ids_` mô tả lá/cụm của mọi dòng train để P01/P02 có thể
dùng cùng structure nhưng tự phân bổ exact budget.
"""

from __future__ import annotations

import importlib
import random
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..base import BaseSelector
from ..contracts import exact_budget_size
from ..result import SelectionResult
from .common import git_commit, prepend_sys_path


class CoreTabNativeSelector(BaseSelector):
    def __init__(self, method_id: str, repo_root: Path, seed: int, options: dict[str, Any] | None = None):
        super().__init__(seed)
        self.method_id = method_id
        self.repo = Path(repo_root) / "coretab"
        self.options = dict(options or {})
        self.structure_parent_ids_: np.ndarray | None = None
        self.candidate_mask_: np.ndarray | None = None

    def select(self, X_train, y_train, budget_ratio, **kwargs):
        self.validate_input(np.asarray(X_train), np.asarray(y_train), budget_ratio)
        requested = exact_budget_size(len(y_train), budget_ratio)
        if not (self.repo / "coretab" / "coreset_algorithms.py").exists():
            return SelectionResult.failure(self.method_id, "blocked", requested, f"Thiếu repo: {self.repo}")
        started = time.perf_counter()
        random.seed(self.seed)
        np.random.seed(self.seed)
        try:
            with prepend_sys_path(self.repo):
                module = importlib.import_module("coretab.coreset_algorithms")
                frame = pd.DataFrame(np.asarray(X_train), index=np.arange(len(y_train)))
                target = pd.Series(np.asarray(y_train), index=frame.index)
                if len(np.unique(y_train)) != 2:
                    self._build_multiclass_structure_only(module, frame, target)
                    elapsed = time.perf_counter() - started
                    failure = SelectionResult.failure(
                        self.method_id, "na_contract", requested,
                        "Native subset CoreTab là binary-only; đã xuất tree structure riêng cho proposed, không tạo native score",
                    )
                    failure.timings = {"structure_only": elapsed, "total": elapsed}
                    failure.diagnostics.update({
                        "upstream_commit": git_commit(self.repo),
                        "structure_only": True,
                        "reference_equivalent_subset": False,
                    })
                    return failure
                if self.method_id == "n01_coretab_dt_subset":
                    model = module.CoreTabDT(
                        sample_percent=float(self.options.get("sample_percent", 0.03)),
                        examples_to_keep=int(self.options.get("examples_to_keep", 1000)),
                    )
                    X_keep, _ = model.create_coreset(frame, target)
                    raw_parent = np.asarray(model.model.apply(frame)).reshape(-1, 1)
                else:
                    model = module.CoreTabXGB(
                        trees_number=int(self.options.get("trees_number", 30)),
                        sample_percent=float(self.options.get("sample_percent", 0.03)),
                        examples_to_keep=int(self.options.get("examples_to_keep", 10_000)),
                        threshold=int(self.options.get("threshold", 1)),
                        params={"objective": "binary:logistic", "seed": self.seed},
                        n_jobs=int(self.options.get("n_jobs", 4)),
                    )
                    X_keep, _ = model.create_coreset(frame, target)
                    matrix = model.get_dmatrix(frame, target)
                    raw_parent = np.asarray(model.model.predict(matrix, pred_leaf=True))
        except (ModuleNotFoundError, ImportError) as error:
            return SelectionResult.failure(self.method_id, "blocked", requested, f"Dependency CoreTab thiếu: {error}")
        except Exception as error:
            return SelectionResult.failure(
                self.method_id, "failed", requested,
                f"CoreTab official trả lỗi; không dùng fallback: {error!r}",
            )
        indices = np.asarray(X_keep.index, dtype=np.int64)
        if len(np.unique(indices)) != len(indices):
            return SelectionResult.failure(self.method_id, "failed", requested, "CoreTab trả index trùng")
        _, parents = np.unique(raw_parent, axis=0, return_inverse=True)
        self.structure_parent_ids_ = parents.astype(np.int64)
        self.candidate_mask_ = np.isin(np.arange(len(y_train)), indices)
        elapsed = time.perf_counter() - started
        return SelectionResult(
            indices=indices,
            weights=np.ones(len(indices), dtype=np.float64),
            requested_rows=requested,
            realized_rows=len(indices),
            budget_mode="native_realized",
            method_id=self.method_id,
            diagnostics={
                "upstream_repo": "https://github.com/avivhadar33/coretab.git",
                "upstream_commit": git_commit(self.repo),
                "reference_equivalent": True,
                "structure_groups": int(len(np.unique(parents))),
                "requested_ratio": float(budget_ratio),
                "realized_ratio": float(len(indices) / len(y_train)),
            },
            timings={"select": elapsed, "total": elapsed},
        )

    def _build_multiclass_structure_only(self, module, frame: pd.DataFrame, target: pd.Series) -> None:
        """Xuất leaf IDs cho proposed; không tuyên bố đây là native CoreTab subset."""
        if self.method_id == "n01_coretab_dt_subset":
            from sklearn.tree import DecisionTreeClassifier
            model = DecisionTreeClassifier(random_state=self.seed)
            model.fit(frame, target)
            raw_parent = np.asarray(model.apply(frame)).reshape(-1, 1)
        else:
            params = {
                "objective": "multi:softprob", "num_class": int(target.nunique()),
                "seed": self.seed, "n_jobs": int(self.options.get("n_jobs", 4)),
            }
            matrix = module.xgb.DMatrix(frame, label=target)
            model = module.xgb.train(
                params, num_boost_round=int(self.options.get("trees_number", 30)), dtrain=matrix
            )
            raw_parent = np.asarray(model.predict(matrix, pred_leaf=True))
        _, parents = np.unique(raw_parent, axis=0, return_inverse=True)
        self.structure_parent_ids_ = parents.astype(np.int64)
        self.candidate_mask_ = np.ones(len(frame), dtype=bool)
