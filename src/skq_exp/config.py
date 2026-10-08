"""File này đọc và kiểm tra cấu hình trước khi một run bắt đầu.

Nó ngăn các lỗi dễ bỏ sót như budget ngoài khoảng cho phép, stage không hợp lệ
hoặc confirmatory run chưa có freeze manifest. Đầu ra là một đối tượng cấu hình
ổn định để các module khác không phải tự đọc JSON theo nhiều cách khác nhau.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


VALID_STAGES = {
    "s0_smoke", "s1_screen", "s2_confirm", "s2_transfer",
    "s3_scale", "s4_temporal", "s5_native",
}


@dataclass(frozen=True)
class ProjectPaths:
    raw_root: Path
    processed_root: Path
    artifact_root: Path
    external_root: Path


@dataclass(frozen=True)
class ExperimentConfig:
    schema_version: int
    experiment_id: str
    protocol_id: str
    stage_id: str
    dataset_ids: tuple[str, ...]
    method_ids: tuple[str, ...]
    learner_ids: tuple[str, ...]
    budget_ratio: float
    split_seed: int
    selector_seeds: tuple[int, ...]
    model_seed: int
    paths: ProjectPaths
    evidence_role: str = "development"
    split_id: str = "registered_split_v1"
    frozen_method_roles: tuple[str, ...] = ()
    test_locked: bool = True
    requires_freeze_manifest: bool = False
    non_inferiority_margin: float = 0.005
    holm_contrasts: int = 5
    resource: dict[str, Any] | None = None
    artifact_policy: dict[str, Any] | None = None
    method_options: dict[str, dict[str, Any]] | None = None

    @classmethod
    def from_json(cls, path: str | Path) -> "ExperimentConfig":
        config_path = Path(path).resolve()
        payload = json.loads(config_path.read_text(encoding="utf-8"))
        if "extends" in payload:
            parent_path = (config_path.parent / payload.pop("extends")).resolve()
            if parent_path == config_path:
                raise ValueError("Config không được extends chính nó")
            parent_payload = json.loads(parent_path.read_text(encoding="utf-8"))
            if "extends" in parent_payload:
                raise ValueError("Chỉ hỗ trợ một tầng extends để config dễ kiểm toán")
            payload = {**parent_payload, **payload}
        base = config_path.parent.parent
        raw_paths = payload.pop("paths")
        raw_paths.setdefault("external_root", "external/repos")
        paths = ProjectPaths(**{
            key: _resolve_path(base, value) for key, value in raw_paths.items()
        })
        config = cls(
            dataset_ids=tuple(payload.pop("dataset_ids")),
            method_ids=tuple(payload.pop("method_ids")),
            learner_ids=tuple(payload.pop("learner_ids")),
            selector_seeds=tuple(int(v) for v in payload.pop("selector_seeds")),
            frozen_method_roles=tuple(payload.pop("frozen_method_roles", ())),
            paths=paths,
            **payload,
        )
        config.validate()
        return config

    def validate(self) -> None:
        if self.schema_version != 3:
            raise ValueError("schema_version phải bằng 3")
        if self.stage_id not in VALID_STAGES:
            raise ValueError(f"stage_id không hợp lệ: {self.stage_id}")
        if not 0 < self.budget_ratio <= 1:
            raise ValueError("budget_ratio phải nằm trong (0, 1]")
        if not self.dataset_ids or not self.method_ids or not self.learner_ids:
            raise ValueError("dataset_ids, method_ids và learner_ids không được rỗng")
        from .data.registry import DATASET_SPECS
        from .methods.registry import METHOD_SPECS

        unknown_datasets = set(self.dataset_ids) - set(DATASET_SPECS)
        if self.stage_id == "s0_smoke":
            unknown_datasets -= {"toy_multiclass_v1"}
        if unknown_datasets:
            raise ValueError(f"Dataset chưa đăng ký: {sorted(unknown_datasets)}")
        unknown_methods = set(self.method_ids) - set(METHOD_SPECS)
        if unknown_methods:
            raise ValueError(f"Method chưa đăng ký: {sorted(unknown_methods)}")
        blocked_status = {
            method_id: METHOD_SPECS[method_id].status
            for method_id in self.method_ids
            if METHOD_SPECS[method_id].status
            not in {"implemented", "derived", "evaluator_only"}
        }
        if blocked_status:
            raise ValueError(f"Config chứa method không runnable: {blocked_status}")
        valid_learners = {"lr", "rf", "xgb", "cat", "mlp"}
        if set(self.learner_ids) - valid_learners:
            raise ValueError(f"Learner chưa đăng ký: {sorted(set(self.learner_ids) - valid_learners)}")
        options = self.method_options or {}
        missing_parent = [
            method_id for method_id in self.method_ids
            if METHOD_SPECS[method_id].needs_parent
            and not options.get(method_id, {}).get("parent_source")
        ]
        if missing_parent:
            raise ValueError(f"Method cần method_options.parent_source: {missing_parent}")
        if not self.selector_seeds or len(set(self.selector_seeds)) != len(self.selector_seeds):
            raise ValueError("selector_seeds phải có ít nhất một giá trị và không trùng")
        if self.stage_id == "s2_confirm":
            if self.budget_ratio != 0.05 or tuple(self.learner_ids) != ("xgb",):
                raise ValueError("confirmatory contract yêu cầu budget 5% và chỉ XGBoost")
            if not self.requires_freeze_manifest:
                raise ValueError("confirmatory run phải yêu cầu freeze manifest")
            if self.test_locked:
                raise ValueError("s2_confirm chỉ được mở test sau freeze (test_locked=false)")
            if set(self.frozen_method_roles) != {"published_reference", "proposed_winner"}:
                raise ValueError(
                    "confirmatory config phải resolve published_reference và proposed_winner từ freeze"
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "experiment_id": self.experiment_id,
            "protocol_id": self.protocol_id,
            "stage_id": self.stage_id,
            "dataset_ids": list(self.dataset_ids),
            "method_ids": list(self.method_ids),
            "learner_ids": list(self.learner_ids),
            "budget_ratio": self.budget_ratio,
            "split_seed": self.split_seed,
            "selector_seeds": list(self.selector_seeds),
            "model_seed": self.model_seed,
            "evidence_role": self.evidence_role,
            "split_id": self.split_id,
            "frozen_method_roles": list(self.frozen_method_roles),
            "test_locked": self.test_locked,
            "requires_freeze_manifest": self.requires_freeze_manifest,
            "non_inferiority_margin": self.non_inferiority_margin,
            "holm_contrasts": self.holm_contrasts,
            "resource": self.resource or {},
            "artifact_policy": self.artifact_policy or {},
            "method_options": self.method_options or {},
            "paths": {
                "raw_root": str(self.paths.raw_root),
                "processed_root": str(self.paths.processed_root),
                "artifact_root": str(self.paths.artifact_root),
                "external_root": str(self.paths.external_root),
            },
        }


def _resolve_path(base: Path, value: str) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (base / path).resolve()

