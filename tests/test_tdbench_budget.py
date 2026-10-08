"""Kiểm tra budget adapter TDBench không bị nhầm với resource gate."""

import numpy as np

from skq_exp.methods.synthetic.tdbench import _classify_resource_exception, _plan_tdbench_budget


def test_kip_adult_uses_largest_source_feasible_budget() -> None:
    y = np.concatenate([
        np.zeros(21_011, dtype=np.int64),
        np.ones(6_665, dtype=np.int64),
    ])
    per_label, diagnostics = _plan_tdbench_budget("s_kip_tdbench", y, 1_384)
    assert per_label == 666
    assert diagnostics["planned_realized_rows"] == 1_332
    assert diagnostics["source_feasibility_limited"] is True
    assert diagnostics["source_max_per_label"] == 666


def test_mtt_keeps_requested_per_class_budget() -> None:
    y = np.concatenate([
        np.zeros(21_011, dtype=np.int64),
        np.ones(6_665, dtype=np.int64),
    ])
    per_label, diagnostics = _plan_tdbench_budget("s_mtt_tdbench", y, 1_384)
    assert per_label == 692
    assert diagnostics["planned_realized_rows"] == 1_384
    assert diagnostics["source_feasibility_limited"] is False


def test_framework_resource_errors_are_not_reported_as_algorithm_failure() -> None:
    assert _classify_resource_exception(RuntimeError("CUDA out of memory")) == "oom"
    assert _classify_resource_exception(RuntimeError("RESOURCE_EXHAUSTED")) == "oom"
    assert _classify_resource_exception(RuntimeError("worker timed out")) == "timeout"
    assert _classify_resource_exception(ValueError("shape mismatch")) is None


def test_empty_training_labels_are_budget_infeasible() -> None:
    per_label, diagnostics = _plan_tdbench_budget(
        "s_kip_tdbench", np.empty(0, dtype=np.int64), 10
    )
    assert per_label == 0
    assert "không có nhãn" in diagnostics["budget_limitation_reason"]
