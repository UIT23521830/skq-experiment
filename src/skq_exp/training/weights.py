"""File này kiểm tra sample weight trước khi train model.

Nó xác nhận trọng số thẳng hàng với dòng được chọn, hữu hạn, không âm và còn tổng
dương. Class weight được tính từ full train rồi nhân với method weight; không tính
lại từ coreset vì việc đó sẽ thay đổi mục tiêu giữa các phương pháp.
"""

from __future__ import annotations

import numpy as np


def balanced_class_weights(y_full_train: np.ndarray) -> dict[int, float]:
    labels, counts = np.unique(y_full_train, return_counts=True)
    total = len(y_full_train)
    return {int(label): total / (len(labels) * count) for label, count in zip(labels, counts)}


def effective_sample_weights(
    selected_y: np.ndarray,
    method_weights: np.ndarray,
    class_weights: dict[int, float] | None,
) -> np.ndarray:
    method_weights = np.asarray(method_weights, dtype=np.float64)
    if method_weights.shape != np.asarray(selected_y).shape:
        raise ValueError("method_weights không thẳng hàng với selected_y")
    multipliers = np.ones(len(selected_y), dtype=np.float64)
    if class_weights:
        multipliers = np.asarray([class_weights[int(label)] for label in selected_y])
    result = method_weights * multipliers
    if np.any(result < 0) or not np.all(np.isfinite(result)) or result.sum() <= 0:
        raise ValueError("effective sample weight không hợp lệ")
    return result

