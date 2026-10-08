"""File này ghép các khối SKQ thành một selector hoàn chỉnh.

Nó chia budget theo structure×class, tạo RFF một lần, chọn dòng bằng herding rồi
tối ưu trọng số trong từng nhóm. Đầu ra giữ exact budget, khối lượng của nhóm và
các chẩn đoán cần để biết phương pháp có thật sự chạy đúng hay không.
"""

from __future__ import annotations

import time

import numpy as np

from ..base import BaseSelector
from ..contracts import BudgetInfeasibleError, exact_budget_size, validate_exact_selection
from ..result import SelectionResult
from .allocation import allocate_groups, make_group_ids
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
        group_ids = make_group_ids(parent_ids, y_train)
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
            groups, capacities, initial_quotas = allocate_groups(group_ids, requested)
            candidate_capacities = np.asarray([
                np.sum((group_ids == group) & candidate_mask) for group in groups
            ], dtype=np.int64)
            quotas = _cap_and_redistribute(initial_quotas, candidate_capacities, capacities, requested)
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
        if query_features is not None:
            query_features = np.asarray(query_features, dtype=np.float32)
            if query_features.ndim == 1:
                query_features = query_features[:, None]
            if len(query_features) != len(y_train):
                raise ValueError("query_features phải có một dòng cho mỗi train row")
            alpha = self.query_alpha
            if not 0.0 <= alpha <= 1.0:
                raise ValueError("query_alpha phải nằm trong [0,1]")
            query_scaled = query_features / np.sqrt(max(1, query_features.shape[1]))
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
                qp_solvers.append(solution.solver)
                weight_parts.append(float(capacity) * solution.weights)
            else:
                weight_parts.append(np.full(int(quota), float(capacity) / int(quota)))
        herding_time = time.perf_counter() - herding_started - qp_time

        if self.use_qp and not qp_converged:
            return SelectionResult.failure(
                self.method_id, "failed", requested,
                "Simplex-QP không hội tụ; không dùng fallback",
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
                "group_capacities": capacities.tolist(),
                "group_quotas": quotas.tolist(),
                "class_coverage": float(class_coverage),
                "max_mass_error": float(max(mass_errors, default=0.0)),
                "rff_components": self.n_components,
                "rff_sigma": rff.sigma_,
                "bandwidth_multiplier": self.bandwidth_multiplier,
                "candidate_rows": int(candidate_mask.sum()),
                "query_alpha": self.query_alpha if query_features is not None else None,
                "query_metadata": query_metadata,
                "qp_objective_mean": float(np.mean(qp_objectives)) if qp_objectives else None,
                "qp_iterations_max": max(qp_iterations, default=0),
                "qp_converged": qp_converged if self.use_qp else None,
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


def _cap_and_redistribute(
    quotas: np.ndarray,
    candidate_capacities: np.ndarray,
    population_capacities: np.ndarray,
    total: int,
) -> np.ndarray:
    """Hạ quota nhóm thiếu candidate rồi phân phần dư cho nhóm còn chỗ."""
    quotas = np.minimum(np.asarray(quotas, dtype=np.int64), candidate_capacities)
    left = int(total - quotas.sum())
    if left < 0:
        raise BudgetInfeasibleError("Quota sau cap vượt budget")
    while left:
        available = candidate_capacities - quotas
        eligible = np.flatnonzero(available > 0)
        if len(eligible) == 0:
            raise BudgetInfeasibleError("Candidate capacity không đủ exact budget")
        scores = population_capacities[eligible] / np.maximum(1, quotas[eligible] + 1)
        chosen = int(eligible[int(np.argmax(scores))])
        quotas[chosen] += 1
        left -= 1
    return quotas

