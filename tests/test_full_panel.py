"""Kiểm tra full config thật sự chứa toàn panel và các contract output tách biệt.

Test dùng mảng nhỏ nên không cần repo nặng. Nó ngăn việc vô tình đổi lệnh `full`
trở lại thành config chỉ có hai method như bản nháp ban đầu.
"""

from pathlib import Path

import numpy as np

from skq_exp.config import ExperimentConfig
from skq_exp.methods import METHOD_SPECS, build_selector
from skq_exp.methods.proposed.query_losses import make_oof_query_losses
from skq_exp.methods.proposed.simplex_qp import solve_simplex_mean_match


ROOT = Path(__file__).resolve().parents[1]


def test_every_registered_method_has_an_explanatory_note():
    """Mỗi method phải tự mô tả vai trò/mức tái hiện để tránh ghi sai trong bài."""
    missing = [method_id for method_id, spec in METHOD_SPECS.items() if not spec.note.strip()]
    assert missing == []


def test_adult_full_config_has_20_rows_and_five_learners():
    config = ExperimentConfig.from_json(ROOT / "configs" / "pilot_adult_full_seed11.json")
    assert len(config.method_ids) == 20
    assert config.learner_ids == ("lr", "rf", "xgb", "cat", "mlp")
    assert set(config.method_ids) <= set(METHOD_SPECS)
    assert {
        METHOD_SPECS[item].output_kind
        for item in ("s_kip_tdbench", "s_mtt_tdbench", "s_tame_official")
    } == {"synthetic"}
    alias = ExperimentConfig.from_json(ROOT / "configs" / "pilot_adult_seed11.json")
    assert alias.method_ids == config.method_ids
    assert config.test_locked is True
    assert config.method_options["p04_skq_lrq_sq"]["parent_source"] == "n02_coretab_xgb_subset"
    assert config.method_options["p05_skq_lrq_mq"]["parent_source"] == "n02_coretab_xgb_subset"
    # KIP/MTT van giu resource gate 500: khong danh doi tinh dung lay viec "chay het".
    assert config.method_options["s_kip_tdbench"]["max_rows"] == 500
    assert config.method_options["s_mtt_tdbench"]["max_rows"] == 500


def test_benchmark_selectors_return_exact_unique_indices(tmp_path):
    rng = np.random.default_rng(7)
    X = rng.normal(size=(80, 6))
    y = np.repeat([0, 1], 40)
    for method_id in ("n_gcoreset_benchmark", "n_leverage_benchmark"):
        selector = build_selector(method_id, 11, external_root=ROOT / "external" / "repos")
        result = selector.select(X, y, 0.1)
        assert result.status == "success"
        assert result.realized_rows == 8
        assert len(np.unique(result.indices)) == 8


def test_oof_query_loss_is_deterministic_and_train_shaped():
    rng = np.random.default_rng(9)
    X = rng.normal(size=(90, 5))
    y = np.repeat([0, 1, 2], 30)
    first, meta = make_oof_query_losses(X, y, ["lr"], seed=11, folds=3, max_threads=1)
    second, _ = make_oof_query_losses(X, y, ["lr"], seed=11, folds=3, max_threads=1)
    assert first.shape == (90, 1)
    assert np.allclose(first, second)
    assert meta["oof_folds"] == 3


def test_simplex_qp_keeps_constraints():
    rng = np.random.default_rng(3)
    selected = rng.normal(size=(12, 7))
    target = rng.normal(size=7)
    solution = solve_simplex_mean_match(selected, target)
    assert solution.converged
    assert np.isclose(solution.weights.sum(), 1.0)
    assert np.all(solution.weights >= -1e-12)
