"""Các baseline hiện đại được review 12/10 yêu cầu cho bảng chính CQ v1.

Không phương pháp nào trong file này được gọi là ``native`` trên dữ liệu CQ:

* Moderate-DS dùng đúng điểm khoảng cách tới median lớp của source ICLR 2023,
  nhưng thay backbone ảnh bằng đặc trưng bảng đã chuẩn hóa.
* CCS gọi đúng bộ lấy mẫu 50 tầng của source ICLR 2023, còn điểm EL2N được
  tính từ xác suất OOF-XGBoost theo quyết định của giảng viên.
* Data-OOB gọi lớp RandomForestDV của source ICML 2023; lớp bọc chỉ vá import
  ``joblib.delayed`` cho scikit-learn mới và lấy các dòng có OOB value cao nhất.
* Kernel Thinning gọi GoodPoints ở commit đã khóa theo từng lớp. Để đạt quota
  bất kỳ, adapter tạo pre-pool xác định có kích thước quota*2^m trước khi gọi
  thuật toán; đây là adaptation được khai báo, không phải paper nguyên trạng.

Mọi dependency/source lỗi đều trả trạng thái riêng; tuyệt đối không fallback sang
một thuật toán khác nhưng vẫn giữ tên baseline.
"""

from __future__ import annotations

import importlib
import importlib.util
import math
import time
from pathlib import Path
from typing import Any

import numpy as np

from ..base import BaseSelector
from ..contracts import exact_budget_size, validate_exact_selection
from ..controls import allocate_largest_remainder
from ..native.common import prepend_sys_path, verify_locked_repo
from ..result import SelectionResult


def _stable_top(values: np.ndarray, size: int, *, largest: bool) -> np.ndarray:
    """Xếp hạng ổn định; index gốc là tie-breaker để tái lập được."""
    values = np.asarray(values, dtype=np.float64)
    primary = -values if largest else values
    return np.lexsort((np.arange(len(values), dtype=np.int64), primary))[:size]


class ModerateDSTabularSelector(BaseSelector):
    """Moderate-DS adapted cho đặc trưng bảng chuẩn hóa, exact budget."""

    method_id = "b_moderate_ds_adapted"

    def __init__(self, repo_root: Path, seed: int, options: dict[str, Any] | None = None):
        super().__init__(seed)
        self.repo = Path(repo_root) / "moderate_ds"
        self.options = dict(options or {})

    def select(self, X_train, y_train, budget_ratio, **kwargs):
        del kwargs
        X = np.asarray(X_train, dtype=np.float64)
        y = np.asarray(y_train)
        self.validate_input(X, y, budget_ratio)
        requested = exact_budget_size(len(y), budget_ratio)
        try:
            upstream_commit = verify_locked_repo(self.repo)
        except RuntimeError as error:
            return SelectionResult.failure(self.method_id, "blocked", requested, str(error))
        started = time.perf_counter()
        distances = np.empty(len(y), dtype=np.float64)
        for label in np.unique(y):
            positions = np.flatnonzero(y == label)
            center = np.median(X[positions], axis=0)
            distances[positions] = np.linalg.norm(X[positions] - center, axis=1)

        # Source trả các index cần loại ở hai đuôi; phần được giữ là cửa sổ
        # trung tâm của thứ tự score. Cách viết này giữ đúng m dòng khi n*rho lẻ.
        ordered = np.lexsort((np.arange(len(y), dtype=np.int64), distances))
        low = (len(y) - requested) // 2
        indices = validate_exact_selection(ordered[low:low + requested], len(y), requested)
        elapsed = time.perf_counter() - started
        return SelectionResult(
            indices=indices,
            weights=np.ones(requested, dtype=np.float64),
            requested_rows=requested,
            realized_rows=requested,
            budget_mode="exact_total",
            method_id=self.method_id,
            diagnostics={
                "adapted": True,
                "native_equivalent": False,
                "upstream_repo": "https://github.com/tmllab/2023_ICLR_Moderate-DS.git",
                "upstream_commit": upstream_commit,
                "upstream_functions": ["get_median", "get_distance", "get_prune_idx"],
                "declared_patches": [
                    "deep image embedding được thay bằng selector_view đã chuẩn hóa",
                    "rounding cửa sổ trung tâm được làm exact-budget và tie-break theo row index",
                ],
                "score": "euclidean_distance_to_class_coordinate_median",
            },
            timings={"select": elapsed, "total": elapsed},
        )


class CCSOOFXGBSelector(BaseSelector):
    """CCS adapted: EL2N từ OOF-XGBoost + stratified sampling upstream."""

    method_id = "b_ccs_oof_xgb_adapted"

    def __init__(self, repo_root: Path, seed: int, options: dict[str, Any] | None = None):
        super().__init__(seed)
        self.repo = Path(repo_root) / "ccs"
        self.options = dict(options or {})

    def select(self, X_train, y_train, budget_ratio, **kwargs):
        del kwargs
        X = np.asarray(X_train, dtype=np.float32)
        y = np.asarray(y_train)
        self.validate_input(X, y, budget_ratio)
        requested = exact_budget_size(len(y), budget_ratio)
        try:
            upstream_commit = verify_locked_repo(self.repo)
        except RuntimeError as error:
            return SelectionResult.failure(self.method_id, "blocked", requested, str(error))
        if importlib.util.find_spec("xgboost") is None:
            return SelectionResult.failure(
                self.method_id, "blocked", requested,
                "CCS adapted bắt buộc dùng OOF-XGBoost; thiếu dependency xgboost",
            )
        if importlib.util.find_spec("torch") is None:
            return SelectionResult.failure(
                self.method_id, "blocked", requested,
                "CCS upstream stratified_sampling cần torch; không fallback sang NumPy",
            )
        started = time.perf_counter()
        try:
            scores, fold_count = self._oof_el2n(X, y)
            indices = self._upstream_stratified(scores, requested)
            indices = validate_exact_selection(indices, len(y), requested)
        except Exception as error:
            return SelectionResult.failure(
                self.method_id, "failed", requested, f"CCS adapted lỗi: {error!r}",
            )
        elapsed = time.perf_counter() - started
        return SelectionResult(
            indices=indices,
            weights=np.ones(requested, dtype=np.float64),
            requested_rows=requested,
            realized_rows=requested,
            budget_mode="exact_total",
            method_id=self.method_id,
            diagnostics={
                "adapted": True,
                "native_equivalent": False,
                "upstream_repo": (
                    "https://github.com/haizhongzheng/"
                    "Coverage-centric-coreset-selection.git"
                ),
                "upstream_commit": upstream_commit,
                "upstream_function": "CoresetSelection.stratified_sampling",
                "declared_patches": [
                    "image training dynamics được thay bằng xác suất OOF-XGBoost",
                    "EL2N được tính trên nhãn multiclass của Pool B",
                ],
                "difficulty_score": "OOF_XGBoost_EL2N",
                "oof_folds": fold_count,
                "device": str(self.options.get("device", "cpu")),
                "score_min": float(scores.min()),
                "score_max": float(scores.max()),
            },
            timings={"select": elapsed, "total": elapsed},
        )

    def _oof_el2n(self, X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, int]:
        from sklearn.model_selection import StratifiedKFold
        from sklearn.preprocessing import LabelEncoder
        from xgboost import XGBClassifier

        encoded = LabelEncoder().fit_transform(y)
        class_counts = np.bincount(encoded)
        folds = min(int(self.options.get("oof_folds", 5)), int(class_counts.min()))
        if folds < 2:
            raise ValueError("Mỗi lớp cần ít nhất 2 dòng để tính OOF")
        splitter = StratifiedKFold(n_splits=folds, shuffle=True, random_state=self.seed)
        probabilities = np.empty((len(y), len(class_counts)), dtype=np.float64)
        params = {
            "n_estimators": int(self.options.get("n_estimators", 200)),
            "max_depth": int(self.options.get("max_depth", 6)),
            "learning_rate": float(self.options.get("learning_rate", 0.1)),
            "subsample": float(self.options.get("subsample", 0.8)),
            "colsample_bytree": float(self.options.get("colsample_bytree", 0.8)),
            "tree_method": "hist",
            "device": str(self.options.get("device", "cpu")),
            "eval_metric": "mlogloss",
            "n_jobs": int(self.options.get("n_jobs", -1)),
        }
        for fold, (fit_idx, hold_idx) in enumerate(splitter.split(X, encoded)):
            model = XGBClassifier(**params, random_state=self.seed + fold)
            model.fit(X[fit_idx], encoded[fit_idx])
            probabilities[hold_idx] = model.predict_proba(X[hold_idx])
        one_hot = np.eye(len(class_counts), dtype=np.float64)[encoded]
        return np.linalg.norm(probabilities - one_hot, axis=1), folds

    def _upstream_stratified(self, scores: np.ndarray, requested: int) -> np.ndarray:
        import torch

        source = self.repo / "core" / "data" / "Coreset.py"
        spec = importlib.util.spec_from_file_location("ccs_upstream_coreset", source)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Không load được source CCS: {source}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        torch.manual_seed(self.seed)
        selected, _ = module.CoresetSelection.stratified_sampling(
            {"el2n": torch.as_tensor(scores, dtype=torch.float64)},
            "el2n",
            requested,
        )
        return np.asarray(selected, dtype=np.int64)


class DataOOBOfficialSelector(BaseSelector):
    """Data-OOB từ source chính thức, chọn exact-budget điểm có value cao nhất."""

    method_id = "b_dataoob_official"

    def __init__(self, repo_root: Path, seed: int, options: dict[str, Any] | None = None):
        super().__init__(seed)
        self.repo = Path(repo_root) / "dataoob"
        self.options = dict(options or {})

    def select(self, X_train, y_train, budget_ratio, **kwargs):
        del kwargs
        X = np.asarray(X_train, dtype=np.float32)
        y = np.asarray(y_train)
        self.validate_input(X, y, budget_ratio)
        requested = exact_budget_size(len(y), budget_ratio)
        try:
            upstream_commit = verify_locked_repo(self.repo)
        except RuntimeError as error:
            return SelectionResult.failure(self.method_id, "blocked", requested, str(error))
        started = time.perf_counter()
        try:
            cls = self._load_upstream_class()
            model = cls(
                n_estimators=int(self.options.get("n_trees", 200)),
                n_jobs=int(self.options.get("n_jobs", -1)),
                random_state=self.seed,
                max_depth=self.options.get("max_depth"),
            )
            model.fit(X, y)
            values = model.evaluate_oob_accuracy(X, y).to_numpy(dtype=np.float64)
            if values.shape != (len(y),) or not np.all(np.isfinite(values)):
                raise RuntimeError("Data-OOB không trả value hữu hạn cho đủ mọi dòng")
            indices = validate_exact_selection(
                _stable_top(values, requested, largest=True), len(y), requested,
            )
        except Exception as error:
            return SelectionResult.failure(
                self.method_id, "failed", requested, f"Data-OOB upstream lỗi: {error!r}",
            )
        elapsed = time.perf_counter() - started
        return SelectionResult(
            indices=indices,
            weights=np.ones(requested, dtype=np.float64),
            requested_rows=requested,
            realized_rows=requested,
            budget_mode="exact_total",
            method_id=self.method_id,
            diagnostics={
                "adapted": True,
                "native_equivalent": False,
                "value_estimator_equivalent": True,
                "upstream_repo": "https://github.com/ykwon0407/dataoob.git",
                "upstream_commit": upstream_commit,
                "upstream_class": "RandomForestClassifierDV",
                "compatibility_patch": (
                    "temporary sklearn.utils.fixes.delayed=joblib.delayed for sklearn>=1.6"
                ),
                "declared_adaptation": (
                    "paper/source trả data values; protocol biến chúng thành subset exact-budget "
                    "bằng stable top-k"
                ),
                "selection_rule": "highest_OOB_value",
                "n_trees": int(self.options.get("n_trees", 200)),
                "value_min": float(values.min()),
                "value_max": float(values.max()),
            },
            timings={"select": elapsed, "total": elapsed},
        )

    def _load_upstream_class(self):
        from joblib import delayed
        import sklearn.utils.fixes as fixes

        source = self.repo / "dataoob" / "ensemble_DV_core.py"
        if not source.exists():
            raise FileNotFoundError(source)
        had_delayed = hasattr(fixes, "delayed")
        old_delayed = getattr(fixes, "delayed", None)
        try:
            fixes.delayed = delayed
            spec = importlib.util.spec_from_file_location("dataoob_upstream_ensemble", source)
            if spec is None or spec.loader is None:
                raise RuntimeError(f"Không load được source Data-OOB: {source}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module.RandomForestClassifierDV
        finally:
            if had_delayed:
                fixes.delayed = old_delayed
            else:
                delattr(fixes, "delayed")


class KernelThinningClasswiseSelector(BaseSelector):
    """Kernel Thinning GoodPoints theo lớp với exact-budget pre-pool công khai."""

    method_id = "b_kernel_thinning_classwise"

    def __init__(self, repo_root: Path, seed: int, options: dict[str, Any] | None = None):
        super().__init__(seed)
        self.repo = Path(repo_root) / "goodpoints"
        self.options = dict(options or {})

    def select(self, X_train, y_train, budget_ratio, **kwargs):
        del kwargs
        X = np.asarray(X_train, dtype=np.float64)
        y = np.asarray(y_train)
        self.validate_input(X, y, budget_ratio)
        requested = exact_budget_size(len(y), budget_ratio)
        try:
            upstream_commit = verify_locked_repo(self.repo)
        except RuntimeError as error:
            return SelectionResult.failure(self.method_id, "blocked", requested, str(error))
        labels, counts = np.unique(y, return_counts=True)
        try:
            quotas = allocate_largest_remainder(counts, requested, ensure_one=True)
        except Exception as error:
            return SelectionResult.failure(
                self.method_id, "budget_infeasible", requested, str(error),
            )
        started = time.perf_counter()
        try:
            with prepend_sys_path(self.repo):
                kt = importlib.import_module("goodpoints.kt")
            selected: list[np.ndarray] = []
            class_runs = []
            for position, (label, capacity, quota) in enumerate(zip(labels, counts, quotas)):
                quota = int(quota)
                capacity = int(capacity)
                rounds = int(math.floor(math.log2(capacity / quota))) if capacity > quota else 0
                pool_size = quota * (2 ** rounds)
                class_indices = np.flatnonzero(y == label)
                class_rng = np.random.default_rng(self.seed + position)
                prepool = np.sort(class_rng.choice(class_indices, size=pool_size, replace=False))
                points = X[prepool]
                bandwidth = self._median_bandwidth(points, self.seed + position)

                def kernel(left, right, scale=bandwidth):
                    left = np.asarray(left, dtype=np.float64)
                    right = np.asarray(right, dtype=np.float64)
                    return np.exp(-np.sum((left - right) ** 2, axis=-1) / (2 * scale ** 2))

                local = np.asarray(kt.thin(
                    points,
                    rounds,
                    kernel,
                    kernel,
                    delta=float(self.options.get("delta", 0.5)),
                    seed=self.seed + position,
                    store_K=False,
                    unique=True,
                    verbose=bool(self.options.get("verbose", False)),
                ), dtype=np.int64)
                if len(local) != quota:
                    raise RuntimeError(
                        f"Lớp {label!r}: GoodPoints trả {len(local)} dòng, quota={quota}"
                    )
                selected.append(prepool[local])
                class_runs.append({
                    "label": label.item() if isinstance(label, np.generic) else label,
                    "capacity": capacity,
                    "quota": quota,
                    "prepool_rows": pool_size,
                    "halving_rounds": rounds,
                    "rbf_bandwidth": bandwidth,
                })
            indices = validate_exact_selection(
                np.concatenate(selected), len(y), requested,
            )
        except (ImportError, ModuleNotFoundError) as error:
            return SelectionResult.failure(
                self.method_id, "blocked", requested,
                f"GoodPoints chưa được build ở commit khóa: {error!r}",
            )
        except Exception as error:
            return SelectionResult.failure(
                self.method_id, "failed", requested, f"Kernel Thinning upstream lỗi: {error!r}",
            )
        elapsed = time.perf_counter() - started
        return SelectionResult(
            indices=indices,
            weights=np.ones(requested, dtype=np.float64),
            requested_rows=requested,
            realized_rows=requested,
            budget_mode="exact_classwise_prepool",
            method_id=self.method_id,
            diagnostics={
                "adapted": True,
                "native_equivalent": False,
                "upstream_repo": "https://github.com/microsoft/goodpoints.git",
                "upstream_commit": upstream_commit,
                "upstream_function": "goodpoints.kt.thin(store_K=False, unique=True)",
                "declared_patches": [
                    "largest-remainder quota theo lớp",
                    "deterministic pre-pool quota*2^m để đạt exact budget bất kỳ",
                    "RBF bandwidth median heuristic trên selector_view chuẩn hóa",
                ],
                "device": "cpu",
                "class_runs": class_runs,
            },
            timings={"select": elapsed, "total": elapsed},
        )

    @staticmethod
    def _median_bandwidth(points: np.ndarray, seed: int) -> float:
        rng = np.random.default_rng(seed)
        size = min(len(points), 2048)
        sample = points[rng.choice(len(points), size=size, replace=False)]
        pairs = min(4096, max(1, size * 2))
        left = sample[rng.integers(0, size, size=pairs)]
        right = sample[rng.integers(0, size, size=pairs)]
        distances = np.linalg.norm(left - right, axis=1)
        positive = distances[distances > 0]
        return float(np.median(positive)) if len(positive) else 1.0
