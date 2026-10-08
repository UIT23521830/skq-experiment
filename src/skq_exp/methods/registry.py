"""File này là danh mục chuẩn của toàn bộ panel thực nghiệm.

Registry phân biệt evaluator, selector dòng thật, generator synthetic, proposed và
ablation. `implemented` nghĩa là đã có đường chạy thật; dependency/resource gate
vẫn có thể trả BLOCKED/OOM trong run chứ không được đổi sang thuật toán khác.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .benchmark import GonzalezBenchmarkSelector, LeverageBenchmarkSelector
from .controls import StratifiedRandomSelector
from .diagnostics import build_d02, build_d04
from .native import AutoCoresetNativeSelector, BDISNativeSelector, CoreTabNativeSelector, CRAIGNativeSelector
from .proposed.structured_kquad import StructuredKQuadSelector
from .synthetic import TAMEOfficialGenerator, TDBenchGenerator


@dataclass(frozen=True)
class MethodSpec:
    method_id: str
    display_name: str
    role: str
    status: str
    needs_parent: bool = False
    output_kind: str = "selection"
    allowed_learners: tuple[str, ...] | None = None
    note: str = ""


METHOD_SPECS = {
    spec.method_id: spec for spec in [
        MethodSpec("c00_full_train", "FullTrain", "reference", "evaluator_only"),
        MethodSpec("c02_stratified_random", "Stratified Random", "control", "implemented", allowed_learners=("xgb",), note="Confirmatory-only theo protocol"),
        MethodSpec("n01_coretab_dt_subset", "CoreTab-DT Official", "native", "implemented"),
        MethodSpec("n02_coretab_xgb_subset", "CoreTab-XGB Official", "native", "implemented"),
        MethodSpec("n_bdis_native", "BDIS-native", "native", "implemented"),
        MethodSpec("n_autocoreset_native", "AutoCoreset-native", "native", "implemented"),
        MethodSpec(
            "n_craig_native", "CRAIG feature-space (retired native label)",
            "native", "retired", note="Không tương đương full official logistic pipeline",
        ),
        MethodSpec(
            "a_craig_feature_space", "CRAIG feature-space adapter",
            "adaptation", "implemented", note="R1 adapter; không claim native equivalence",
        ),
        MethodSpec("n_gcoreset_benchmark", "Gonzalez Coreset benchmark", "benchmark", "implemented"),
        MethodSpec("n_leverage_benchmark", "Leverage benchmark", "benchmark", "implemented"),
        MethodSpec("s_kip_tdbench", "KIP-TDBench", "synthetic", "implemented", output_kind="synthetic"),
        MethodSpec("s_mtt_tdbench", "MTT-TDBench", "synthetic", "implemented", output_kind="synthetic"),
        MethodSpec("s_tame_official", "TAME official", "synthetic", "implemented", output_kind="synthetic"),
        MethodSpec("p00_structured_kquad", "Structured KQuad engine", "engine", "not_runnable"),
        MethodSpec("p01_skq_coretab_dt", "SKQ-CoreTab-DT", "proposed", "implemented", True),
        MethodSpec("p02_skq_coretab_xgb", "SKQ-CoreTab-XGB", "proposed", "implemented", True),
        MethodSpec("p03_skq_bdis_filtered", "SKQ-BDIS-Filtered", "proposed", "implemented", True),
        MethodSpec("p04_skq_lrq_sq", "SKQ-LRQ-SQ", "proposed", "implemented", True),
        MethodSpec("p05_skq_lrq_mq", "SKQ-LRQ-MQ", "proposed", "implemented", True),
        MethodSpec("d02_parent_structured_random", "Parent-Structured Random", "ablation", "implemented", True),
        MethodSpec("d04_global_rff_quadrature", "Global RFF Quadrature", "ablation", "implemented"),
        MethodSpec("d05_equal_group_weight", "Equal-Within-Group Weight", "ablation", "derived", True),
    ]
}


def get_method_spec(method_id: str) -> MethodSpec:
    try:
        return METHOD_SPECS[method_id]
    except KeyError as error:
        raise KeyError(f"Method chưa đăng ký: {method_id}") from error


def build_selector(method_id: str, seed: int, *, n_components: int = 256, external_root: str | Path | None = None, options: dict[str, Any] | None = None):
    spec = get_method_spec(method_id)
    if spec.status != "implemented":
        raise RuntimeError(f"{method_id} không phải selector trực tiếp: status={spec.status}")
    options = dict(options or {})
    repo_root = Path(external_root or "external/repos")
    if method_id == "c02_stratified_random":
        return StratifiedRandomSelector(seed)
    if method_id in {"n01_coretab_dt_subset", "n02_coretab_xgb_subset"}:
        return CoreTabNativeSelector(method_id, repo_root, seed, options)
    if method_id == "n_bdis_native":
        return BDISNativeSelector(repo_root, seed, options)
    if method_id == "n_autocoreset_native":
        return AutoCoresetNativeSelector(repo_root, seed, options)
    if method_id == "a_craig_feature_space":
        return CRAIGNativeSelector(repo_root, seed, options)
    if method_id == "n_gcoreset_benchmark":
        return GonzalezBenchmarkSelector(repo_root, seed)
    if method_id == "n_leverage_benchmark":
        return LeverageBenchmarkSelector(repo_root, seed)
    if method_id == "d02_parent_structured_random":
        return build_d02(seed, n_components)
    if method_id == "d04_global_rff_quadrature":
        return build_d04(seed, n_components)
    if method_id in {"p01_skq_coretab_dt", "p02_skq_coretab_xgb", "p03_skq_bdis_filtered", "p04_skq_lrq_sq", "p05_skq_lrq_mq"}:
        default_alpha = 0.5 if method_id in {"p04_skq_lrq_sq", "p05_skq_lrq_mq"} else 1.0
        return StructuredKQuadSelector(
            method_id, seed=seed, n_components=n_components,
            bandwidth_multiplier=float(options.get("bandwidth_multiplier", 1.0)),
            query_alpha=float(options.get("query_alpha", default_alpha)),
        )
    raise RuntimeError(f"Factory chưa có implementation cho {method_id}")


def build_generator(method_id: str, seed: int, *, external_root: str | Path, options: dict[str, Any] | None = None):
    spec = get_method_spec(method_id)
    if spec.output_kind != "synthetic" or spec.status != "implemented":
        raise RuntimeError(f"{method_id} không phải generator synthetic runnable")
    if method_id == "s_tame_official":
        return TAMEOfficialGenerator(Path(external_root), seed, options)
    return TDBenchGenerator(method_id, Path(external_root), seed, options)
