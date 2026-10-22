"""Calibration phải dựa trên đo thật đủ replicate và không tạo timeout dự báo."""

from __future__ import annotations

import json

from skq_exp.experiments.resource_calibration import (
    CALIBRATION_ROWS,
    CalibrationObservation,
    DeviceMetadata,
    fit_scaling_model,
    gate_decision,
)
from scripts.run_cq_v1_resource_calibration import (
    CANDIDATE_METHODS,
    FIXED_METHODS,
    _load_observations,
    _observation_payload,
    _resolve_budget_ratio,
)


DEVICE = DeviceMetadata(
    cpu="test-cpu",
    gpu="test-gpu",
    ram_bytes=24 * 1024**3,
    vram_bytes=16 * 1024**3,
    max_threads=4,
    environment_id="fixture-v1",
    provider="kaggle-free",
    gpu_count=2,
    accelerator_policy="gpu-t4",
)


def _observations(multiplier: float = 0.0001):
    return tuple(
        CalibrationObservation(
            selector_id="selector-a",
            rows=rows,
            budget_rows=max(1, rows // 20),
            replicate=replicate,
            warmup_seconds=2.0,
            steady_seconds=rows * multiplier * (1 + 0.01 * replicate),
            peak_rss_bytes=rows * 1024,
            peak_vram_bytes=rows * 128,
            device=DEVICE,
        )
        for rows in CALIBRATION_ROWS
        for replicate in range(1, 4)
    )


def test_complete_calibration_fits_prediction_and_preserves_replicates() -> None:
    fitted = fit_scaling_model(_observations(), target_rows=2_000_000)
    assert fitted["fit_status"] == "fitted"
    assert len(fitted["observations"]) == 9
    assert fitted["upper_prediction_seconds"] >= fitted["predicted_seconds"]
    assert fitted["time_model"]["slope"] > 0
    assert fitted["observations"][0]["allocated_gpu_hours"] > 0


def test_missing_replicate_requires_more_measurement_not_operations() -> None:
    fitted = fit_scaling_model(_observations()[:-1], target_rows=2_000_000)
    decision = gate_decision(fitted, supports_sharding=True)
    assert decision["decision"] == "needs_more_calibration"
    assert decision["run_status"] is None
    assert "operations" in decision["reason"]


def test_upper_bound_over_cap_requests_shard_without_timeout_status() -> None:
    fitted = fit_scaling_model(_observations(multiplier=0.02), target_rows=2_000_000)
    decision = gate_decision(
        fitted, supports_sharding=True, selector_cap_seconds=100,
    )
    assert decision["decision"] == "run_shared_shard_wrapper"
    assert decision["run_status"] is None


def test_resource_checkpoint_round_trip_and_rejects_other_environment(tmp_path) -> None:
    observations = list(_observations())
    path = tmp_path / "observations_selector-a.json"
    path.write_text(
        json.dumps(_observation_payload(observations)),
        encoding="utf-8",
    )
    loaded = _load_observations(
        path, method_id="selector-a", environment_id="fixture-v1",
    )
    assert loaded == observations
    try:
        _load_observations(
            path, method_id="selector-a", environment_id="different-machine",
        )
    except ValueError as error:
        assert "environment khác" in str(error)
    else:
        raise AssertionError("Checkpoint không được trộn environment")


def test_qd16_panel_has_exactly_ten_fixed_and_three_candidates() -> None:
    assert len(FIXED_METHODS) == 10
    assert len(CANDIDATE_METHODS) == 3
    assert len(set(FIXED_METHODS + CANDIDATE_METHODS)) == 13


def test_budget_ratio_is_read_from_locked_dev_headroom(tmp_path) -> None:
    path = tmp_path / "headroom_decision.json"
    path.write_text(json.dumps({
        "evidence_split": "dev",
        "test_data_read": False,
        "rho_star": 0.005,
        "repository_commit": "abc",
        "allowed_inputs": ["FullTrain-B", "C02"],
    }), encoding="utf-8")
    ratio, source = _resolve_budget_ratio(0.02, str(path))
    assert ratio == 0.005
    assert source["mode"] == "headroom_evidence"
