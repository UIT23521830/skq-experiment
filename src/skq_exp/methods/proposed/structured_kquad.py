"""Engine của các phương pháp SKQ do đề tài này đề xuất.

Trạng thái: implementation của nhóm tác giả dự án, không phải code từ paper đối
chứng. P01/P02 dùng cấu trúc CoreTab, P03 dùng candidate BDIS, còn P04/P05 thêm
query-loss ngoài-fold sau khi base winner đã được freeze. Cơ chế chung: chia exact
budget theo structure×class, ánh xạ RFF, chọn dòng thật bằng kernel herding rồi
tối ưu trọng số simplex-QP trong từng nhóm. Loại đầu ra: subset dòng thật có trọng
số và đúng tổng budget.

Các biến thể này là đóng góp chính cần được so với native, benchmark, synthetic
và control. P04/P05 bị GATE_LOCKED trước dev freeze để tránh chọn cấu hình sau khi
đã nhìn test; gate đó là quy tắc phương pháp luận, không phải code chưa hoàn tất.
"""

from __future__ import annotations

import time

import numpy as np

from ..base import BaseSelector
from ..contracts import BudgetInfeasibleError, exact_budget_size, validate_exact_selection
from ..result import SelectionResult
from .allocation import allocate_classwise
from .herding import kernel_herding
from .rff import RBFRandomFeatures
from .simplex_qp import solve_simplex_mean_match


class StructuredKQuadSelector(BaseSelector):
    def __init__(
        self,
        method_id: str,
        seed: int = 11,
        n_components: int = 256,
        bandwidth_multiplier: float = 1.0,
        use_qp: bool = True,
        random_within_group: bool = False,
        query_alpha: float = 1.0,
    ):
        super().__init__(seed)
        self.method_id = method_id
        self.n_components = int(n_components)
        self.bandwidth_multiplier = float(bandwidth_multiplier)
        self.use_qp = bool(use_qp)
        self.random_within_group = bool(random_within_group)
        self.query_alpha = float(query_alpha)

    def select(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        budget_ratio: float,
        *,
        parent_ids: np.ndarray | None = None,
        row_ids: np.ndarray | None = None,
        resource_guard=None,
        candidate_mask: np.ndarray | None = None,
        query_features: np.ndarray | None = None,
        query_metadata: dict | None = None,
        **kwargs,
    ) -> SelectionResult:
        self.validate_input(X_train, y_train, budget_ratio)
        started = time.perf_counter()
        requested = exact_budget_size(len(y_train), budget_ratio)
        if requested < len(np.unique(y_train)):
            return SelectionResult.failure(
                self.method_id, "budget_infeasible", requested,
                "Budget nhỏ hơn số lớp nên không thể bảo đảm class coverage",
            )
        row_ids = np.arange(len(y_train), dtype=np.int64) if row_ids is None else np.asarray(row_ids)
        candidate_mask = (
            np.ones(len(y_train), dtype=bool)
            if candidate_mask is None else np.asarray(candidate_mask, dtype=bool)
        )
        if candidate_mask.shape != y_train.shape:
            raise ValueError("candidate_mask phải cùng chiều y_train")
        if int(candidate_mask.sum()) < requested:
            return SelectionResult.failure(
                self.method_id, "budget_infeasible", requested,
                "Candidate pool nhỏ hơn exact budget",
            )
        try:
            allocation = allocate_classwise(parent_ids, y_train, candidate_mask, requested)
            group_ids = allocation.group_ids
            groups = allocation.groups
            capacities = allocation.population_capacities
            candidate_capacities = allocation.candidate_capacities
            quotas = allocation.quotas
        except BudgetInfeasibleError as error:
            return SelectionResult.failure(
                self.method_id, "budget_infeasible", requested, str(error)
            )

        rff_started = time.perf_counter()
        rff = RBFRandomFeatures(
            n_components=self.n_components,
            bandwidth_multiplier=self.bandwidth_multiplier,
            seed=self.seed,
        )
        check = resource_guard.check if resource_guard is not None else None
        Z = rff.fit_transform(np.asarray(X_train), check=check)
        kernel_scale = float(np.sqrt(np.mean(np.sum(np.asarray(Z, dtype=np.float64) ** 2, axis=1))))
        if not np.isfinite(kernel_scale) or kernel_scale <= 0:
            raise ValueError("RFF block có train mean-squared norm không hợp lệ")
        Z = Z / kernel_scale
        query_scale = None
        if query_features is not None:
            query_features = np.asarray(query_features, dtype=np.float32)
            if query_features.ndim == 1:
                query_features = query_features[:, None]
            if len(query_features) != len(y_train):
                raise ValueError("query_features phải có một dòng cho mỗi train row")
            alpha = self.query_alpha
            if alpha not in {0.25, 0.5, 0.75}:
                raise ValueError("LRQ query_alpha phải thuộc {0.25, 0.50, 0.75}")
            query_scale = float(np.sqrt(np.mean(np.sum(query_features.astype(np.float64) ** 2, axis=1))))
            if not np.isfinite(query_scale) or query_scale <= 0:
                raise ValueError("Query block có train mean-squared norm không hợp lệ")
            query_scaled = query_features / query_scale
            Z = np.concatenate([
                np.sqrt(alpha) * Z,
                np.sqrt(1.0 - alpha) * query_scaled,
            ], axis=1)
        rff_time = time.perf_counter() - rff_started

        selected_parts: list[np.ndarray] = []
        weight_parts: list[np.ndarray] = []
        qp_objectives: list[float] = []
        qp_iterations: list[int] = []
        qp_converged = True
        qp_sum_violations: list[float] = []
        qp_min_weights: list[float] = []
        qp_solvers: list[str] = []
        herding_started = time.perf_counter()
        qp_time = 0.0
        for group, capacity, quota in zip(groups, capacities, quotas):
            if quota == 0:
                continue
            full_pool = np.flatnonzero(group_ids == group)
            pool = np.flatnonzero((group_ids == group) & candidate_mask)
            if self.random_within_group:
                local = self.rng.choice(len(pool), size=int(quota), replace=False)
            else:
                local = kernel_herding(
                    Z[pool], int(quota), row_ids[pool], self.seed, check=check
                )
            picked = pool[local]
            selected_parts.append(picked)
            if self.use_qp:
                qp_started = time.perf_counter()
                solution = solve_simplex_mean_match(
                    Z[picked], Z[full_pool].mean(axis=0), check=check
                )
                qp_time += time.perf_counter() - qp_started
                qp_objectives.append(solution.objective)
                qp_iterations.append(solution.iterations)
                qp_converged = qp_converged and solution.converged
                qp_sum_violations.append(solution.sum_violation)
                qp_min_weights.append(solution.min_weight)
                qp_solvers.append(solution.solver)
                weight_parts.append(float(capacity) * solution.weights)
            else:
                weight_parts.append(np.full(int(quota), float(capacity) / int(quota)))
        herding_time = time.perf_counter() - herding_started - qp_time

        qp_constraints_valid = (
            max(qp_sum_violations, default=0.0) <= 1e-8
            and min(qp_min_weights, default=0.0) >= -1e-10
        )
        if self.use_qp and (not qp_converged or not qp_constraints_valid):
            return SelectionResult.failure(
                self.method_id, "failed", requested,
                "Simplex-QP không hội tụ hoặc vi phạm simplex tolerance; không dùng fallback",
            )
        indices = validate_exact_selection(
            np.concatenate(selected_parts), len(y_train), requested
        )
        weights = np.concatenate(weight_parts)
        class_coverage = len(np.unique(y_train[indices])) / len(np.unique(y_train))
        mass_errors = []
        for group, capacity in zip(groups, capacities):
            mask = group_ids[indices] == group
            mass_errors.append(abs(weights[mask].sum() - capacity) / max(1, int(capacity)))
        max_mass_error = float(max(mass_errors, default=0.0))
        total_mass_error = float(abs(weights.sum() - len(y_train)) / max(1, len(y_train)))
        if max_mass_error > 1e-8 or total_mass_error > 1e-8:
            return SelectionResult.failure(
                self.method_id, "failed", requested,
                "Trọng số không bảo toàn population mass sau coarsening",
            )
        total_time = time.perf_counter() - started
        return SelectionResult(
            indices=indices,
            weights=weights,
            requested_rows=requested,
            realized_rows=requested,
            budget_mode="exact_total",
            method_id=self.method_id,
            diagnostics={
                "n_groups": int(len(groups)),
                **allocation.diagnostics,
                "group_capacities": capacities.tolist(),
                "group_candidate_capacities": candidate_capacities.tolist(),
                "group_quotas": quotas.tolist(),
                "class_coverage": float(class_coverage),
                "max_mass_error": max_mass_error,
                "total_mass_error": total_mass_error,
                "rff_components": self.n_components,
                "rff_sigma": rff.sigma_,
                "rff_landmark_row_ids": row_ids[rff.landmark_indices_].astype(np.int64).tolist(),
                "rff_dtype": str(Z.dtype),
                "kernel_block_scale": kernel_scale,
                "query_block_scale": query_scale,
                "bandwidth_multiplier": self.bandwidth_multiplier,
                "candidate_rows": int(candidate_mask.sum()),
                "query_alpha": self.query_alpha if query_features is not None else None,
                "query_metadata": query_metadata,
                "qp_objective_mean": float(np.mean(qp_objectives)) if qp_objectives else None,
                "qp_iterations_max": max(qp_iterations, default=0),
                "qp_converged": qp_converged if self.use_qp else None,
                "qp_constraint_valid": qp_constraints_valid if self.use_qp else None,
                "qp_max_sum_violation": max(qp_sum_violations, default=0.0) if self.use_qp else None,
                "qp_min_weight": min(qp_min_weights, default=0.0) if self.use_qp else None,
                "qp_solvers": sorted(set(qp_solvers)) if self.use_qp else None,
                "normalized_ess": float(weights.sum() ** 2 / (len(weights) * np.sum(weights ** 2))),
            },
            timings={
                "rff": rff_time,
                "herding": max(0.0, herding_time),
                "qp": qp_time,
                "total": total_time,
            },
        )
