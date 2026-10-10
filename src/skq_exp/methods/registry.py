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
from .proposed.sharded_merge_reduce import ShardedMergeReduceSelector
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
        MethodSpec(
            "c00_full_train", "FullTrain", "reference", "evaluator_only",
            note="Mốc trần dùng toàn bộ train; không phải phương pháp nén.",
        ),
        MethodSpec(
            "c02_stratified_random", "Stratified Random", "control", "implemented",
            allowed_learners=("xgb",),
            note=(
                "Control cổ điển: subset thật, exact budget. Contract cũ chỉ chạy XGBoost; "
                "config full-v2 ghi đè rõ ràng để đánh giá đủ năm learner."
            ),
        ),
        MethodSpec(
            "n01_coretab_dt_subset", "CoreTab-DT Official", "native", "implemented",
            note="Official-source adapter; subset thật theo kích thước native CoreTab-DT.",
        ),
        MethodSpec(
            "n02_coretab_xgb_subset", "CoreTab-XGB Official", "native", "implemented",
            note="Official-source adapter; subset thật theo kích thước native CoreTab-XGB.",
        ),
        MethodSpec(
            "n_bdis_native", "BDIS-native", "native", "implemented",
            note="Official-source adapter; subset thật, cần faiss và giữ realized size upstream.",
        ),
        MethodSpec(
            "n_autocoreset_native", "AutoCoreset-native", "native", "implemented",
            note="Official-source adapter qua driver riêng; subset thật có trọng số và artifact gate.",
        ),
        MethodSpec(
            "n_craig_native", "CRAIG feature-space (retired native label)",
            "native", "retired", note="Không tương đương full official logistic pipeline",
        ),
        MethodSpec(
            "a_craig_feature_space", "CRAIG feature-space adapter",
            "adaptation", "implemented",
            note="R1 feature-space adaptation; dùng upstream lazy-greedy, không claim native equivalence.",
        ),
        MethodSpec(
            "n_gcoreset_benchmark", "Gonzalez Coreset benchmark", "benchmark", "implemented",
            note="Benchmark-source adapter; farthest-first subset thật, không phải native paper source.",
        ),
        MethodSpec(
            "n_leverage_benchmark", "Leverage benchmark", "benchmark", "implemented",
            note="Benchmark-source adapter; PCA leverage subset thật, không phải native paper source.",
        ),
        MethodSpec(
            "s_kip_tdbench", "KIP-TDBench", "synthetic", "implemented",
            output_kind="synthetic",
            note="TDBench-source adapter; sinh dữ liệu bằng kernel inducing points, có dependency/resource gate.",
        ),
        MethodSpec(
            "s_mtt_tdbench", "MTT-TDBench", "synthetic", "implemented",
            output_kind="synthetic",
            note=(
                "Benchmark-source adapter có 7 patch khai báo; khôi phục gradient, "
                "snapshot và RNG cho trajectory matching; không phải TDBench nguyên trạng."
            ),
        ),
        MethodSpec(
            "s_gm_tdbench", "Gradient Matching-TDBench", "synthetic", "implemented",
            output_kind="synthetic",
            note=(
                "Benchmark-source adapter cho Dataset Condensation with Gradient Matching "
                "(ICLR 2021); vá requires_grad bị thiếu trong source TDBench và khai báo patch."
            ),
        ),
        MethodSpec(
            "s_datm_tdbench", "DATM-TDBench", "synthetic", "implemented",
            output_kind="synthetic",
            note=(
                "Benchmark-source adapter cho Difficulty-Aligned Trajectory Matching "
                "(ICLR 2024); dùng source TDBench với các patch gradient/snapshot/RNG khai báo."
            ),
        ),
        MethodSpec(
            "s_tame_official", "TAME official", "synthetic", "implemented",
            output_kind="synthetic",
            note="Official-source synthesis adapter; distribution matching, không claim full-paper reproduction.",
        ),
        MethodSpec(
            "p00_structured_kquad", "Structured KQuad engine", "engine", "not_runnable",
            note="Engine nội bộ của SKQ; không phải một dòng độc lập trong bảng utility.",
        ),
        MethodSpec(
            "p01_skq_coretab_dt", "SKQ-CoreTab-DT", "proposed", "implemented", True,
            note="Đề xuất: structure CoreTab-DT + RFF herding + simplex-QP.",
        ),
        MethodSpec(
            "p02_skq_coretab_xgb", "SKQ-CoreTab-XGB", "proposed", "implemented", True,
            note="Đề xuất: structure CoreTab-XGB + RFF herding + simplex-QP.",
        ),
        MethodSpec(
            "p03_skq_bdis_filtered", "SKQ-BDIS-Filtered", "proposed", "implemented", True,
            note=(
                "Đề xuất: candidate BDIS + phân bổ có cấu trúc + RFF herding + "
                "simplex-QP; realized=min(mục tiêu 5%, BDIS pool) và báo cáo size thực."
            ),
        ),
        MethodSpec(
            "p04_skq_lrq_sq", "SKQ-LRQ-SQ", "proposed", "implemented", True,
            note=(
                "Đề xuất query-aware một learner; được screen trên dev với parent "
                "khai báo trước, test chỉ mở sau freeze."
            ),
        ),
        MethodSpec(
            "p05_skq_lrq_mq", "SKQ-LRQ-MQ", "proposed", "implemented", True,
            note=(
                "Đề xuất query-aware nhiều learner; được screen trên dev với parent "
                "khai báo trước, test chỉ mở sau freeze."
            ),
        ),
        MethodSpec(
            "p06_gonzalez_qp", "Gonzalez-QP", "proposed", "implemented", True,
            note=(
                "Đề xuất screening: giữ candidate Gonzalez đúng 5%, dùng Voronoi theo "
                "Gonzalez anchor và simplex-QP; tách riêng để đo đóng góp của weighting."
            ),
        ),
        MethodSpec(
            "p07_skq_gonzalez", "SKQ-Gonzalez", "proposed", "implemented", True,
            note=(
                "Đề xuất coverage-aware: Gonzalez tạo candidate pool 2x budget, "
                "SKQ RFF herding + simplex-QP nén về exact budget."
            ),
        ),
        MethodSpec(
            "p08_skq_gonzalez_lrq_sq", "SKQ-Gonzalez-LRQ-SQ", "proposed", "implemented", True,
            note=(
                "Đề xuất coverage/query-aware một learner: candidate Gonzalez 2x, "
                "OOF-LR query loss, RFF herding và simplex-QP; dev screen trước freeze."
            ),
        ),
        MethodSpec(
            "p09_skq_gonzalez_lrq_mq", "SKQ-Gonzalez-LRQ-MQ", "proposed", "implemented", True,
            note=(
                "Đề xuất coverage/query-aware nhiều learner: candidate Gonzalez 2x, "
                "OOF LR/RF/XGB query loss, RFF herding và simplex-QP; dev screen trước freeze."
            ),
        ),
        MethodSpec(
            "p10_skq_mr_coretab_xgb", "SKQ-MR-CoreTab-XGB", "proposed", "implemented",
            note=(
                "Đề xuất scale-out: CoreTab-XGB tạo leaf structure theo shard xác định, "
                "sau đó SKQ streaming cấp exact budget toàn cục; dùng toàn bộ train, không proxy."
            ),
        ),
        MethodSpec(
            "p11_skq_mr_bdis", "SKQ-MR-BDIS", "proposed", "implemented",
            note=(
                "Đề xuất scale-out: BDIS tạo candidate theo shard, SKQ streaming reduce toàn cục; "
                "giữ realized size khi candidate pool nhỏ, không pad/trùng và không proxy."
            ),
        ),
        MethodSpec(
            "d02_parent_structured_random", "Parent-Structured Random", "ablation", "implemented", True,
            note="Ablation: giữ structure và QP nhưng thay kernel herding bằng random.",
        ),
        MethodSpec(
            "d04_global_rff_quadrature", "Global RFF Quadrature", "ablation", "implemented",
            note="Ablation: bỏ parent structure, giữ class + RFF herding + QP.",
        ),
        MethodSpec(
            "d05_equal_group_weight", "Equal-Within-Group Weight", "ablation", "derived", True,
            note="Ablation: giữ index winner, thay simplex-QP bằng trọng số đều trong nhóm.",
        ),
    ]
}


def get_method_spec(method_id: str) -> MethodSpec:
    try:
        return METHOD_SPECS[method_id]
    except KeyError as error:
        raise KeyError(f"Method chưa đăng ký: {method_id}") from error


def allowed_learners_for(
    method_id: str, options: dict[str, Any] | None = None,
) -> tuple[str, ...] | None:
    """Trả contract learner, cho phép protocol mới ghi đè contract legacy.

    Override nằm trong config và vì vậy đi vào protocol hash/artifact. Cách này
    giữ nguyên hành vi của config v1 nhưng cho phép full-v2 mở control ngẫu nhiên
    trên đủ learner mà không sửa thuật toán chọn mẫu.
    """
    configured = dict(options or {}).get("allowed_learners")
    if configured is not None:
        return tuple(str(item) for item in configured)
    return get_method_spec(method_id).allowed_learners


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
    if method_id in {
        "p01_skq_coretab_dt", "p02_skq_coretab_xgb", "p03_skq_bdis_filtered",
        "p04_skq_lrq_sq", "p05_skq_lrq_mq", "p06_gonzalez_qp",
        "p07_skq_gonzalez", "p08_skq_gonzalez_lrq_sq",
        "p09_skq_gonzalez_lrq_mq",
    }:
        default_alpha = 0.5 if method_id in {
            "p04_skq_lrq_sq", "p05_skq_lrq_mq",
            "p08_skq_gonzalez_lrq_sq", "p09_skq_gonzalez_lrq_mq",
        } else 1.0
        return StructuredKQuadSelector(
            method_id, seed=seed, n_components=n_components,
            bandwidth_multiplier=float(options.get("bandwidth_multiplier", 1.0)),
            query_alpha=float(options.get("query_alpha", default_alpha)),
            budget_policy=str(options.get("budget_policy", "exact_total")),
        )
    if method_id in {"p10_skq_mr_coretab_xgb", "p11_skq_mr_bdis"}:
        return ShardedMergeReduceSelector(
            method_id,
            repo_root,
            seed=seed,
            options=options,
            n_components=n_components,
        )
    raise RuntimeError(f"Factory chưa có implementation cho {method_id}")


def build_generator(method_id: str, seed: int, *, external_root: str | Path, options: dict[str, Any] | None = None):
    spec = get_method_spec(method_id)
    if spec.output_kind != "synthetic" or spec.status != "implemented":
        raise RuntimeError(f"{method_id} không phải generator synthetic runnable")
    if method_id == "s_tame_official":
        return TAMEOfficialGenerator(Path(external_root), seed, options)
    return TDBenchGenerator(method_id, Path(external_root), seed, options)
