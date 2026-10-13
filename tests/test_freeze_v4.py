"""Freeze v4 khóa candidate/config/data và không cho sửa nội dung."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from skq_exp.config import ExperimentConfig, ProjectPaths
from skq_exp.cli import main as cli_main
from skq_exp.experiments import freeze as freeze_module
from skq_exp.experiments.freeze import (
    create_freeze_manifest_v4,
    validate_freeze_manifest_v4,
)
from skq_exp.experiments.provenance import protocol_hash
from skq_exp.methods.registry import METHOD_SPECS


def _configs(tmp_path: Path, monkeypatch):
    root = Path(__file__).parents[1]
    source = ExperimentConfig.from_json(root / "configs" / "s0_smoke.json")
    processed = tmp_path / "processed" / "toy_multiclass_v1"
    processed.mkdir(parents=True)
    for name, payload in {
        "preprocessing_manifest.json": {"snapshot": "cq-v1-fixture"},
        "split_manifest.json": {"split": "fixture"},
        "feature_contract.json": {"contract_hash": "fixture"},
    }.items():
        (processed / name).write_text(json.dumps(payload), encoding="utf-8")
    paths = ProjectPaths(
        raw_root=tmp_path / "raw",
        processed_root=tmp_path / "processed",
        artifact_root=tmp_path / "artifacts",
        external_root=tmp_path / "external",
    )
    candidate = "x_coretab_mc_cell"
    monkeypatch.setitem(
        freeze_module.METHOD_SPECS,
        candidate,
        replace(
            METHOD_SPECS[candidate],
            role="proposed",
            status="implemented",
            evidence_role="dev_selection",
            confirmatory_allowed=True,
        ),
    )
    dev = replace(
        source,
        paths=paths,
        test_locked=True,
        method_ids=(candidate, "c02_stratified_random", "c03_phase_class_random"),
        learner_ids=("xgb",),
        learner_params={"xgb": {"max_depth": 4}},
        early_stopping={"enabled": True, "source": "dev", "patience": 20},
        selector_seeds=(11, 29, 47),
    )
    confirmatory = replace(dev, evidence_role="confirmatory", test_locked=False)
    monkeypatch.setattr(freeze_module, "_git_commit", lambda _root: "abc123")
    return dev, confirmatory, candidate


def test_freeze_v4_roundtrip_and_tamper_detection(tmp_path: Path, monkeypatch) -> None:
    dev, confirmatory, candidate = _configs(tmp_path, monkeypatch)
    output = create_freeze_manifest_v4(
        dev,
        candidate_list=(candidate,),
        selected_candidate=candidate,
        published_reference="c02_stratified_random",
        strongest_baseline="c03_phase_class_random",
        confirmatory_config_hash=protocol_hash(confirmatory),
        rho_star=0.01,
        selection_evidence_hash="a" * 64,
        stats_protocol_hash="b" * 64,
        shard_policy={"rows": 200_000, "shared": True},
        allowed_extensions=("adult_transfer",),
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    validate_freeze_manifest_v4(payload, confirmatory)
    assert payload["schema_version"] == 4
    assert payload["selected_candidate"] == candidate
    assert payload["test_access_policy"]["confirmatory_unlocks_allowed"] == 1
    payload["rho_star"] = 0.05
    with pytest.raises(RuntimeError, match="manifest_id"):
        validate_freeze_manifest_v4(payload, confirmatory)


def test_freeze_v4_rejects_unapproved_candidate(tmp_path: Path, monkeypatch) -> None:
    dev, confirmatory, candidate = _configs(tmp_path, monkeypatch)
    monkeypatch.setitem(
        freeze_module.METHOD_SPECS, candidate,
        replace(freeze_module.METHOD_SPECS[candidate], confirmatory_allowed=False),
    )
    with pytest.raises(ValueError, match="chưa được phép confirmatory"):
        create_freeze_manifest_v4(
            dev,
            candidate_list=(candidate,),
            selected_candidate=candidate,
            published_reference="c02_stratified_random",
            strongest_baseline="c03_phase_class_random",
            confirmatory_config_hash=protocol_hash(confirmatory),
            rho_star=0.01,
            selection_evidence_hash="a" * 64,
            stats_protocol_hash="b" * 64,
            shard_policy={"rows": 200_000},
            allowed_extensions=(),
        )


def test_freeze_v4_cli_requires_complete_spec(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    spec = tmp_path / "incomplete.json"
    spec.write_text('{"candidate_list": []}', encoding="utf-8")
    with pytest.raises(ValueError, match="spec thiếu trường"):
        cli_main([
            "freeze-v4",
            "--config", str(root / "configs" / "s0_smoke.json"),
            "--spec", str(spec),
        ])
