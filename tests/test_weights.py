"""Các test này kiểm tra method weight và class weight được ghép đúng cách.

Trọng số 1 phải giữ đúng class multiplier, còn weight 0 phải loại đóng góp của mẫu
đó khỏi loss. Shape sai hoặc tổng trọng số bằng 0 phải bị từ chối.
"""

import numpy as np
import pytest

from skq_exp.training.weights import balanced_class_weights, effective_sample_weights


def test_effective_weight_is_product() -> None:
    y_full = np.array([0, 0, 0, 1])
    classes = balanced_class_weights(y_full)
    result = effective_sample_weights(
        np.array([0, 1]), np.array([2.0, 3.0]), classes
    )
    assert np.allclose(result, [2.0 * classes[0], 3.0 * classes[1]])


def test_invalid_weight_is_rejected() -> None:
    with pytest.raises(ValueError):
        effective_sample_weights(np.array([0, 1]), np.array([0.0, 0.0]), None)

