"""Endpoint hai cấp của CQ v1: enrollment utility và course quality.

UL dùng Macro-F1 cấp lượt ghi danh. EC dùng MAE của Q-hat cấp khóa theo PCC,
chỉ trên khóa có ít nhất ``n_min`` người học. Hàm giữ P1 riêng và trung bình P1–P4;
CC/course-equal chỉ là sensitivity, không thay endpoint chính.
"""

from __future__ import annotations

from typing import Any, Literal

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score

from ..data.cq_protocol import CLASSES, quality_class


PRIVATE_PREDICTION_COLUMNS = {
    "run_id", "course_id", "course_root_id", "learner_id", "phase",
    "q_true", "y_true", "y_pred", "p_E", "p_G", "p_A",
}


def validate_private_predictions(frame: pd.DataFrame) -> dict[str, Any]:
    """Kiểm schema prediction private; không ghi row-level artifact ra public."""
    missing = sorted(PRIVATE_PREDICTION_COLUMNS - set(frame.columns))
    if missing:
        raise KeyError(f"Prediction schema thiếu cột: {missing}")
    probabilities = frame[["p_E", "p_G", "p_A"]].to_numpy(dtype=float)
    if (
        not np.all(np.isfinite(probabilities))
        or np.any(probabilities < 0)
        or not np.allclose(probabilities.sum(axis=1), 1.0, atol=1e-6)
    ):
        raise ValueError("Probability E/G/A không hợp lệ")
    if not set(frame["phase"].unique()) <= {"P1", "P2", "P3", "P4"}:
        raise ValueError("phase ngoài P1–P4")
    if frame.duplicated(["run_id", "course_id", "learner_id", "phase"]).any():
        raise ValueError("Prediction bị trùng enrollment/phase trong cùng run")
    return {
        "schema_version": 1,
        "rows": int(len(frame)),
        "run_ids": int(frame["run_id"].nunique()),
        "row_level_visibility": "private_only",
    }


def class_conditional_means(
    train_enrollments: pd.DataFrame,
    *,
    q_col: str = "q",
    y_col: str = "y",
) -> dict[str, float]:
    """Tính mu_y một lần từ enrollment khóa train, không lặp theo phase."""
    means = train_enrollments.groupby(y_col)[q_col].mean().reindex(CLASSES)
    if means.isna().any():
        raise ValueError("Mỗi lớp phải có enrollment trong train")
    values = {label: float(means[label]) for label in CLASSES}
    if not values["E"] < values["G"] < values["A"]:
        raise ValueError("Hằng số protocol phải thỏa mu_E < mu_G < mu_A")
    return values


def course_truth(
    enrollments: pd.DataFrame,
    *,
    course_col: str = "course_id",
) -> pd.DataFrame:
    """Qc=mean qkc, Yc=tau(Qc), cùng số enrollment nc."""
    truth = enrollments.groupby(course_col)["q"].agg(Q_true="mean", n_learners="size")
    truth["Y_true"] = quality_class(truth["Q_true"].to_numpy())
    return truth


def course_estimates(
    predictions: pd.DataFrame,
    mu: dict[str, float],
    *,
    mode: Literal["pcc", "cc"] = "pcc",
    course_col: str = "course_id",
) -> pd.DataFrame:
    """PCC là endpoint chính; CC chỉ dùng sensitivity."""
    probabilities = predictions[["p_E", "p_G", "p_A"]].to_numpy(dtype=float)
    if mode == "cc":
        probabilities = np.eye(len(CLASSES))[probabilities.argmax(axis=1)]
    elif mode != "pcc":
        raise ValueError(f"mode không hợp lệ: {mode}")
    columns = [f"pihat_{label}" for label in CLASSES]
    prevalence = pd.DataFrame(
        probabilities, index=predictions[course_col].to_numpy(), columns=columns,
    ).groupby(level=0).mean()
    mu_vector = np.asarray([mu[label] for label in CLASSES], dtype=float)
    prevalence["Q_hat"] = prevalence[columns].to_numpy() @ mu_vector
    prevalence["Y_hat"] = quality_class(prevalence["Q_hat"].to_numpy())
    return prevalence


def cq_endpoints(
    predictions: pd.DataFrame,
    mu: dict[str, float],
    *,
    n_min: int,
    mode: Literal["pcc", "cc"] = "pcc",
) -> dict[str, Any]:
    """Tính UL/EC theo phase và summary đăng ký trước."""
    validate_private_predictions(predictions)
    if n_min <= 0:
        raise ValueError("n_min phải dương và được khóa tại M0")
    per_phase: dict[str, dict[str, Any]] = {}
    for phase in ("P1", "P2", "P3", "P4"):
        frame = predictions[predictions["phase"] == phase]
        if frame.empty:
            raise ValueError(f"Thiếu prediction phase {phase}")
        ul = float(f1_score(frame["y_true"], frame["y_pred"], labels=CLASSES, average="macro", zero_division=0))
        enrollment_truth = frame[["course_id", "learner_id", "q_true", "y_true"]].rename(
            columns={"q_true": "q", "y_true": "y"},
        )
        truth = course_truth(enrollment_truth)
        estimate = course_estimates(frame, mu, mode=mode)
        joined = truth.join(estimate, how="inner")
        eligible = joined[joined["n_learners"] >= n_min].copy()
        if eligible.empty:
            ec = None
            signed_error = None
            course_macro_f1 = None
        else:
            errors = eligible["Q_hat"] - eligible["Q_true"]
            ec = float(errors.abs().mean())
            signed_error = float(errors.mean())
            course_macro_f1 = float(f1_score(
                eligible["Y_true"], eligible["Y_hat"], labels=CLASSES,
                average="macro", zero_division=0,
            ))
        per_phase[phase] = {
            "ul_macro_f1": ul,
            "ec_mae_pcc" if mode == "pcc" else "ec_mae_cc": ec,
            "signed_course_error": signed_error,
            "course_macro_f1_sensitivity": course_macro_f1,
            "eligible_courses": int(len(eligible)),
            "all_courses": int(len(joined)),
        }
    ec_key = "ec_mae_pcc" if mode == "pcc" else "ec_mae_cc"
    ec_values = [row[ec_key] for row in per_phase.values() if row[ec_key] is not None]
    return {
        "schema_version": 1,
        "mode": mode,
        "n_min": int(n_min),
        "per_phase": per_phase,
        "ul_mean_p1_p4": float(np.mean([row["ul_macro_f1"] for row in per_phase.values()])),
        "ul_p1_secondary": per_phase["P1"]["ul_macro_f1"],
        "ec_mean_p1_p4": float(np.mean(ec_values)) if len(ec_values) == 4 else None,
        "ec_missing_phase_count": int(4 - len(ec_values)),
    }
