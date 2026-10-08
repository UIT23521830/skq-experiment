"""Các test này kiểm tra method quá lớn bị chặn trước khi chiếm RAM hoặc CPU.

Ước lượng không thay thế benchmark thật, nhưng phải bảo thủ và có thể cấu hình.
Run vượt ngưỡng được ghi trạng thái dự báo thay vì làm máy treo.
"""

import pytest

from skq_exp.resources import ResourceLimitError, enforce_preflight, estimate_selection_cost


def test_preflight_blocks_memory_heavy_run() -> None:
    estimate = estimate_selection_cost(
        "d04_global_rff_quadrature", 10_000_000, 100, 500_000,
        rff_components=1024, n_classes=2,
    )
    with pytest.raises(ResourceLimitError) as caught:
        enforce_preflight(estimate, {"max_ram_gb": 1, "max_estimated_operations": 1e20})
    assert caught.value.status == "predicted_oom"


def test_preflight_blocks_operation_heavy_run() -> None:
    estimate = estimate_selection_cost(
        "a_craig_feature_space", 1_000, 20, 1_000, rff_components=1, n_classes=10
    )
    with pytest.raises(ResourceLimitError) as caught:
        enforce_preflight(estimate, {"max_ram_gb": 128, "max_estimated_operations": 1e6})
    assert caught.value.status == "predicted_timeout"


def test_kip_memory_estimate_includes_target_kernel_and_gradients() -> None:
    budget = 1_384
    estimate = estimate_selection_cost(
        "s_kip_tdbench", 27_676, 100, budget, rff_components=1, n_classes=2
    )
    # Riêng target-support kernel float64 đã là 10 * budget^2 * 8 byte;
    # estimate phải lớn hơn mức đó vì còn gradient và optimizer.
    raw_target_kernel = 10 * budget ** 2 * 8
    assert estimate.working_bytes > raw_target_kernel
