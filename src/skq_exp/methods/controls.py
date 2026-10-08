"""Đối chứng ngẫu nhiên phân tầng cho bảng so sánh.

Trạng thái: code nội bộ, không phải phương pháp đề xuất và không tuyên bố tái hiện
một paper cụ thể. Cơ chế: chia exact budget theo tỷ lệ lớp rồi lấy mẫu ngẫu nhiên
không hoàn lại. Loại đầu ra: tập con gồm các dòng thật, trọng số bằng nhau. Phương
pháp được đưa vào bài làm mốc cổ điển để kiểm tra SKQ có tốt hơn việc lấy mẫu ngẫu
nhiên nhưng vẫn bảo toàn phân bố nhãn hay không.
"""

from __future__ import annotations

import time

import numpy as np

from .base import BaseSelector
from .contracts import BudgetInfeasibleError, exact_budget_size, validate_exact_selection
from .result import SelectionResult


def allocate_largest_remainder(capacities: np.ndarray, total: int, ensure_one: bool = True) -> np.ndarray:
    capacities = np.asarray(capacities, dtype=np.int64)
    if total > int(capacities.sum()):
        raise BudgetInfeasibleError("Budget lớn hơn tổng capacity")
    active = capacities > 0
    minimum = active.astype(np.int64) if ensure_one else np.zeros_like(capacities)
    if int(minimum.sum()) > total:
        raise BudgetInfeasibleError("Budget nhỏ hơn số nhóm/lớp cần phủ")
    remaining = total - int(minimum.sum())
    free = capacities - minimum
    if remaining == 0:
        return minimum
    shares = remaining * capacities / capacities.sum()
    extra = np.minimum(np.floor(shares).astype(np.int64), free)
    allocation = minimum + extra
    left = total - int(allocation.sum())
    remainders = shares - np.floor(shares)
    order = np.lexsort((np.arange(len(capacities)), -remainders))
    while left:
        progressed = False
        for index in order:
            if allocation[index] < capacities[index]:
                allocation[index] += 1
                left -= 1
                progressed = True
                if left == 0:
                    break
        if not progressed:
            raise BudgetInfeasibleError("Không thể phân bổ exact budget trong capacity")
    return allocation


class StratifiedRandomSelector(BaseSelector):
    method_id = "c02_stratified_random"

    def select(self, X_train: np.ndarray, y_train: np.ndarray, budget_ratio: float, **kwargs) -> SelectionResult:
        self.validate_input(X_train, y_train, budget_ratio)
        started = time.perf_counter()
        requested = exact_budget_size(len(y_train), budget_ratio)
        labels, counts = np.unique(y_train, return_counts=True)
        quotas = allocate_largest_remainder(counts, requested, ensure_one=True)
        chosen = []
        for label, quota in zip(labels, quotas):
            pool = np.flatnonzero(y_train == label)
            chosen.extend(self.rng.choice(pool, size=int(quota), replace=False).tolist())
        indices = validate_exact_selection(np.asarray(chosen), len(y_train), requested)
        self.rng.shuffle(indices)
        return SelectionResult(
            indices=indices,
            weights=np.ones(requested, dtype=np.float64),
            requested_rows=requested,
            realized_rows=requested,
            budget_mode="exact_total",
            method_id=self.method_id,
            diagnostics={
                "labels": labels.tolist(),
                "class_capacities": counts.tolist(),
                "class_quotas": quotas.tolist(),
            },
            timings={"select": time.perf_counter() - started},
        )
