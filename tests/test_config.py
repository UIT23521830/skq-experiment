"""Các test này kiểm tra config sai bị chặn trước khi tạo artifact.

Chúng tập trung vào confirmatory contract vì một lỗi budget hoặc learner ở bước
này có thể làm toàn bộ bảng kết quả không còn đúng protocol.
"""

from pathlib import Path

from skq_exp.config import ExperimentConfig


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

