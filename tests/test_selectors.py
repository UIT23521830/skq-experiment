"""Các test này kiểm tra selector giữ đúng budget, row ID và trọng số.

Dữ liệu nhỏ đủ để test chạy nhanh nhưng vẫn có nhiều lớp và parent group. Nếu một
thay đổi làm trùng index, mất lớp hoặc sai tổng khối lượng, test phải dừng ngay.
"""

import numpy as np

from skq_exp.data.toy import make_toy_data
from skq_exp.methods.controls import StratifiedRandomSelector
from skq_exp.methods.proposed.structured_kquad import StructuredKQuadSelector


def test_stratified_random_exact_and_deterministic() -> None:
    data = make_toy_data()
    first = StratifiedRandomSelector(11).select(data["X_train"], data["y_train"], 0.05)
    second = StratifiedRandomSelector(11).select(data["X_train"], data["y_train"], 0.05)
    assert first.status == "success"
    assert len(first.indices) == round(len(data["y_train"]) * 0.05)
    assert np.array_equal(first.indices, second.indices)
    assert len(np.unique(data["y_train"][first.indices])) == 3


def test_structured_kquad_preserves_budget_and_mass() -> None:
    data = make_toy_data()
    selector = StructuredKQuadSelector(
        "p01_skq_coretab_dt", seed=11, n_components=64
    )
    result = selector.select(
        data["X_train"], data["y_train"], 0.05,
        parent_ids=data["parent_train"], row_ids=data["row_ids_train"],
    )
    assert result.status == "success"
    assert len(result.indices) == result.requested_rows
    assert len(np.unique(result.indices)) == len(result.indices)
    assert np.isclose(result.weights.sum(), len(data["y_train"]), atol=1e-5)
    assert result.diagnostics["class_coverage"] == 1.0
    assert result.diagnostics["max_mass_error"] < 1e-6

