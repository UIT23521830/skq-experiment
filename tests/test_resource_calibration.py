"""Calibration phải dựa trên đo thật đủ replicate và không tạo timeout dự báo."""

from __future__ import annotations

from skq_exp.experiments.resource_calibration import (
    CALIBRATION_ROWS,
    CalibrationObservation,
    DeviceMetadata,
    fit_scaling_model,
    gate_decision,
)


DEVICE = DeviceMetadata(
    cpu="test-cpu",
    gpu="test-gpu",
    ram_bytes=24 * 1024**3,
    vram_bytes=16 * 1024**3,
    max_threads=4,
    environment_id="fixture-v1",
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
