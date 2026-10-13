"""Kiểm tra metadata khoa học không bị đổi thành claim bằng ghi chú tự do."""

from skq_exp.methods.registry import METHOD_SPECS


def test_coretab_native_is_explicitly_binary_only() -> None:
    for method_id in ("n01_coretab_dt_subset", "n02_coretab_xgb_subset"):
        spec = METHOD_SPECS[method_id]
        assert spec.task_contract == "binary_only"
        assert spec.fidelity_tier == "official_source_adapter"
        assert spec.budget_contract == "native_realized"


def test_historical_p_variants_are_not_confirmatory() -> None:
    for method_id in (
        "p01_skq_coretab_dt", "p02_skq_coretab_xgb", "p03_skq_bdis_filtered",
        "p04_skq_lrq_sq", "p05_skq_lrq_mq", "p06_gonzalez_qp",
        "p07_skq_gonzalez", "p08_skq_gonzalez_lrq_sq",
        "p09_skq_gonzalez_lrq_mq", "p10_skq_mr_coretab_xgb",
        "p11_skq_mr_bdis",
    ):
        assert METHOD_SPECS[method_id].confirmatory_allowed is False


def test_pending_coretab_multiclass_candidate_is_disabled() -> None:
    spec = METHOD_SPECS["x_coretab_mc_cell"]
    assert spec.status == "experimental_disabled"
    assert spec.evidence_role == "exploratory"
    assert spec.confirmatory_allowed is False
    assert spec.task_contract == "multiclass"


def test_c01_c03_are_controls_not_proposed_methods() -> None:
    for method_id in ("c01_uniform_random", "c03_phase_class_random"):
        spec = METHOD_SPECS[method_id]
        assert spec.role == "control"
        assert spec.fidelity_tier == "local_reimplementation"
        assert spec.confirmatory_allowed is True

