"""Các test này kiểm tra config sai bị chặn trước khi tạo artifact.

Chúng tập trung vào confirmatory contract vì một lỗi budget hoặc learner ở bước
này có thể làm toàn bộ bảng kết quả không còn đúng protocol.
"""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from skq_exp.config import ExperimentConfig
from skq_exp.experiments.runner import _validate_lrq_gate


def test_smoke_config_loads() -> None:
    path = Path(__file__).parents[1] / "configs" / "s0_smoke.json"
    config = ExperimentConfig.from_json(path)
    assert config.stage_id == "s0_smoke"
    assert config.budget_ratio == 0.05
    assert config.paths.artifact_root.name == "artifacts"


def test_confirmatory_contract_is_locked() -> None:
    path = Path(__file__).parents[1] / "configs" / "s2_confirm.json"
    config = ExperimentConfig.from_json(path)
    assert config.learner_ids == ("xgb",)
    assert config.requires_freeze_manifest is True
    assert config.non_inferiority_margin == 0.005


def test_unknown_method_is_rejected(tmp_path: Path) -> None:
    source = Path(__file__).parents[1] / "configs" / "s0_smoke.json"
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["method_ids"] = ["unknown_method"]
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="Method chưa đăng ký"):
        ExperimentConfig.from_json(path)


def test_lrq_can_screen_on_locked_dev_but_not_unlocked_test() -> None:
    root = Path(__file__).parents[1]
    config = ExperimentConfig.from_json(root / "configs" / "pilot_adult_full_seed11.json")
    options = config.method_options["p04_skq_lrq_sq"]
    reason, provenance = _validate_lrq_gate(config, options, freeze_manifest=None)
    assert reason is None
    assert provenance["selection_phase"] == "pre_freeze_dev_screen"
    assert provenance["confirmatory_eligible"] is False

    reason, _ = _validate_lrq_gate(replace(config, test_locked=False), options, None)
    assert "test_locked=true" in reason

    registered_screen = ExperimentConfig.from_json(root / "configs" / "s1_screen.json")
    assert {"p04_skq_lrq_sq", "p05_skq_lrq_mq"} <= set(registered_screen.method_ids)


def test_lrq_confirmatory_still_requires_matching_freeze() -> None:
    root = Path(__file__).parents[1]
    config = ExperimentConfig.from_json(root / "configs" / "s2_confirm.json")
    options = {"parent_source": "n02_coretab_xgb_subset"}
    reason, _ = _validate_lrq_gate(config, options, freeze_manifest=None)
    assert "freeze" in reason

    freeze = {
        "base_winner_method_id": "p02_skq_coretab_xgb",
        "base_winner_structure_source": "n02_coretab_xgb_subset",
    }
    reason, provenance = _validate_lrq_gate(config, options, freeze)
    assert reason is None
    assert provenance["parent_frozen"] is True
    assert provenance["confirmatory_eligible"] is True


def test_lrq_temporal_accepts_multiple_predeclared_parent_sources() -> None:
    root = Path(__file__).parents[1]
    config = ExperimentConfig.from_json(
        root / "configs" / "pilot_course_quality_med_temporal_seed11_v4.json"
    )
    freeze = {
        "base_winner_method_id": "p02_skq_coretab_xgb",
        "base_winner_structure_source": "n02_coretab_xgb_subset",
        "allowed_parent_sources": ["n02_coretab_xgb_subset", "gonzalez_pool_2x"],
    }
    for method_id in (
        "p04_skq_lrq_sq", "p05_skq_lrq_mq",
        "p08_skq_gonzalez_lrq_sq", "p09_skq_gonzalez_lrq_mq",
    ):
        reason, provenance = _validate_lrq_gate(
            config, config.method_options[method_id], freeze
        )
        assert reason is None
        assert provenance["parent_frozen"] is True
        assert provenance["frozen_parent_source"] == config.method_options[method_id]["parent_source"]
