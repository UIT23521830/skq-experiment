"""Kiểm tra contract weight và early stopping của protocol V2.

Các test dùng learner giả để xác nhận dev được truyền đúng đường và không cần cài
XGBoost/CatBoost/Torch trên máy chạy unit test.
"""

from __future__ import annotations

import numpy as np
import pytest

from skq_exp.methods.result import SelectionResult
from skq_exp.training import evaluator as evaluator_module
from skq_exp.training.evaluator import fit_selection_learner


class _EarlyStopLearner:
    def __init__(self) -> None:
        self.fit_kwargs = None
        self.best_iteration = 7

    def fit(self, X, y, **kwargs):
        del X, y
        self.fit_kwargs = kwargs
        return self


def _selection() -> SelectionResult:
    return SelectionResult(
        indices=np.array([0, 1, 2]),
        weights=np.array([1.0, 2.0, 3.0]),
        requested_rows=3,
        realized_rows=3,
        budget_mode="exact_total",
        method_id="test_selector",
    )


def test_xgb_early_stopping_uses_dev_and_records_best_iteration(monkeypatch) -> None:
    learner = _EarlyStopLearner()
    build_kwargs = {}

    def _build(*args, **kwargs):
        del args
        build_kwargs.update(kwargs)
        return learner

    monkeypatch.setattr(evaluator_module, "build_learner", _build)
    X_train = np.arange(12, dtype=np.float32).reshape(3, 4)
    y_train = np.array([0, 1, 1])
    X_dev = np.ones((2, 4), dtype=np.float32)
    y_dev = np.array([0, 1])

    fitted = fit_selection_learner(
        _selection(),
        X_train,
        y_train,
        learner_id="xgb",
        X_inner_val=X_dev,
        y_inner_val=y_dev,
        early_stopping={"enabled": True, "source": "dev", "patience": 13},
    )

    assert build_kwargs["params"]["early_stopping_rounds"] == 13
    assert learner.fit_kwargs["eval_set"][0][0] is X_dev
    assert learner.fit_kwargs["eval_set"][0][1] is y_dev
    assert fitted.base_cost["early_stopping_source"] == "dev"
    assert fitted.base_cost["best_iteration"] == 7


def test_early_stopping_rejects_missing_dev(monkeypatch) -> None:
    monkeypatch.setattr(
        evaluator_module, "build_learner", lambda *args, **kwargs: _EarlyStopLearner(),
    )
    with pytest.raises(ValueError, match="thiếu dev split"):
        fit_selection_learner(
            _selection(),
            np.arange(12, dtype=np.float32).reshape(3, 4),
            np.array([0, 1, 1]),
            learner_id="xgb",
            early_stopping={"enabled": True, "source": "dev", "patience": 10},
        )


def test_natural_class_policy_keeps_only_relative_method_weights(monkeypatch) -> None:
    learner = _EarlyStopLearner()
    monkeypatch.setattr(evaluator_module, "build_learner", lambda *args, **kwargs: learner)
    fitted = fit_selection_learner(
        _selection(),
        np.arange(12, dtype=np.float32).reshape(3, 4),
        np.array([0, 1, 1]),
        learner_id="lr",
        class_weight_policy="natural",
    )
    expected = np.array([0.5, 1.0, 1.5])
    assert np.allclose(learner.fit_kwargs["sample_weight"], expected)
    assert fitted.base_cost["class_weight_policy"] == "natural"


def test_legacy_config_does_not_silently_enable_mlp_early_stopping(monkeypatch) -> None:
    learner = _EarlyStopLearner()
    monkeypatch.setattr(evaluator_module, "build_learner", lambda *args, **kwargs: learner)
    fit_selection_learner(
        _selection(),
        np.arange(12, dtype=np.float32).reshape(3, 4),
        np.array([0, 1, 1]),
        learner_id="mlp",
        X_inner_val=np.ones((2, 4), dtype=np.float32),
        y_inner_val=np.array([0, 1]),
        early_stopping=None,
    )
    assert learner.fit_kwargs["eval_set"] is None
