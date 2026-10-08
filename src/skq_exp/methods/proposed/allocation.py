"""File này chia exact budget cho các nhóm structure×class.

Nhóm có nhiều mẫu nhận quota lớn hơn nhưng không vượt capacity. Quy tắc đảm bảo
tổng quota đúng budget; nếu budget không đủ để phủ các lớp bắt buộc, code dừng và
báo rõ thay vì tự thay đổi thiết lập.
"""

from __future__ import annotations

import numpy as np

from ..controls import allocate_largest_remainder


def make_group_ids(parent_ids: np.ndarray | None, y: np.ndarray) -> np.ndarray:
    y = np.asarray(y)
    if parent_ids is None:
        _, encoded = np.unique(y, return_inverse=True)
        return encoded.astype(np.int64)
    parent_ids = np.asarray(parent_ids)
    if len(parent_ids) != len(y):
        raise ValueError("parent_ids phải cùng số dòng với y")
    pairs = np.asarray([f"{p}|{label}" for p, label in zip(parent_ids, y)], dtype=object)
    _, encoded = np.unique(pairs, return_inverse=True)
    return encoded.astype(np.int64)


def allocate_groups(group_ids: np.ndarray, total: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    groups, counts = np.unique(group_ids, return_counts=True)
    # Group coverage chỉ được yêu cầu nếu budget đủ; class coverage được kiểm riêng ở selector.
    quotas = allocate_largest_remainder(counts, total, ensure_one=total >= len(groups))
    return groups, counts, quotas

