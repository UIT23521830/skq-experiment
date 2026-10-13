"""Tạo freeze manifest từ lựa chọn được khai báo rõ trước khi mở test.

Lệnh này không tự chọn winner. Người chạy phải truyền method/structure và lý do
freeze; với CQ có thể ghi rõ đây là cấu hình chuyển giao từ Adult. Cách này tránh
việc cell Kaggle tự viết JSON không kiểm tra fingerprint hoặc commit.
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

from ..artifacts import atomic_json, sha256_file, stable_hash
from ..config import ExperimentConfig
from ..methods import METHOD_SPECS
from .provenance import dataset_fingerprint, protocol_hash


REVIEW_HASHES = {
    "2026-10-12": "3C48CAAA4024FF9A7D19F948428142586BE0097849319B45B056BE39880538AB",
    "2026-10-13": "35F6CE05910ACEB5777610B482FC9D12BD14FF35E0E0FD8590D26C79970E8EA2",
}


def create_freeze_manifest(
    config: ExperimentConfig,
    *,
    base_winner_method_id: str,
    base_winner_structure_source: str,
    published_reference: str,
    proposed_winner: str,
    selection_basis: str,
    allowed_parent_sources: tuple[str, ...] = (),
    overwrite: bool = False,
) -> Path:
    """Ghi manifest schema v3 sau khi kiểm tra method và processed snapshot."""
    chosen = {
        "base_winner_method_id": base_winner_method_id,
        "base_winner_structure_source": base_winner_structure_source,
        "published_reference": published_reference,
        "proposed_winner": proposed_winner,
    }
    for role, method_id in chosen.items():
        spec = METHOD_SPECS.get(method_id)
        if spec is None or spec.status in {"not_runnable", "retired"}:
            raise ValueError(f"Freeze {role} không trỏ tới method runnable: {method_id}")
        if method_id not in config.method_ids:
            raise ValueError(f"Freeze {role} không có trong config: {method_id}")
    if not selection_basis.strip():
        raise ValueError("Freeze cần selection_basis mô tả nguồn lựa chọn")

    # Một temporal panel có thể chứa nhiều nhánh LRQ đã được khai báo trước,
    # ví dụ CoreTab-LRQ và Gonzalez-LRQ. Danh sách này chỉ mở đúng các parent
    # đã có trong config; nó không tự chọn winner và không đọc metric test.
    configured_parent_sources = {
        str(options.get("parent_source"))
        for options in (config.method_options or {}).values()
        if options.get("parent_source")
        and not str(options.get("parent_source")).startswith("@")
    }
    frozen_parent_sources = tuple(dict.fromkeys(
        (base_winner_structure_source, *allowed_parent_sources)
    ))
    invalid_parent_sources = [
        source for source in frozen_parent_sources
        if source not in config.method_ids and source not in configured_parent_sources
    ]
    if invalid_parent_sources:
        raise ValueError(
            "Freeze chứa parent source không có trong config: "
            f"{invalid_parent_sources}"
        )

    commit = _git_commit(Path(__file__).resolve().parents[3])
    if commit is None:
        raise RuntimeError("Không đọc được Git commit để khóa freeze manifest")
    output = config.paths.artifact_root / "freeze" / "freeze_manifest.json"
    if output.exists() and not overwrite:
        raise FileExistsError(f"Freeze manifest đã tồn tại: {output}")
    atomic_json(output, {
        "schema_version": 3,
        "config_hash": protocol_hash(config),
        "code_commit": commit,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "selection_basis": selection_basis,
        "source_experiment_id": config.experiment_id,
        "source_stage_id": config.stage_id,
        "base_winner_method_id": base_winner_method_id,
        "base_winner_structure_source": base_winner_structure_source,
        "allowed_parent_sources": list(frozen_parent_sources),
        "method_roles": {
            "published_reference": published_reference,
            "proposed_winner": proposed_winner,
        },
        "dataset_fingerprints": {
            dataset_id: dataset_fingerprint(config, dataset_id)
            for dataset_id in config.dataset_ids
        },
    })
    return output


def create_freeze_manifest_v4(
    config: ExperimentConfig,
    *,
    candidate_list: tuple[str, ...],
    selected_candidate: str,
    published_reference: str,
    strongest_baseline: str,
    confirmatory_config_hash: str,
    rho_star: float,
    selection_evidence_hash: str,
    stats_protocol_hash: str,
    shard_policy: dict,
    allowed_extensions: tuple[str, ...],
    previous_manifest_id: str | None = None,
    deviations: tuple[dict, ...] = (),
    plan_version: str = "2.0.0",
) -> Path:
    """Tạo M1 freeze v4; không overwrite và không tự chọn candidate."""
    if config.test_locked is not True:
        raise ValueError("Freeze v4 phải tạo khi test còn khóa")
    if not 1 <= len(candidate_list) <= 3 or len(set(candidate_list)) != len(candidate_list):
        raise ValueError("candidate_list phải có 1–3 method không trùng")
    if selected_candidate not in candidate_list:
        raise ValueError("selected_candidate phải nằm trong candidate_list")
    if not 0 < rho_star <= 1:
        raise ValueError("rho_star phải nằm trong (0,1]")
    for name, value in {
        "confirmatory_config_hash": confirmatory_config_hash,
        "selection_evidence_hash": selection_evidence_hash,
        "stats_protocol_hash": stats_protocol_hash,
    }.items():
        if not _is_sha256(value):
            raise ValueError(f"{name} phải là SHA-256 hex")
    if not config.learner_params:
        raise ValueError("Freeze v4 cần learner_params đã tune trên FullTrain-B")
    if not config.early_stopping or not config.early_stopping.get("enabled"):
        raise ValueError("Freeze v4 cần early_stopping policy đã bật trên dev")
    if config.early_stopping.get("source") != "dev":
        raise ValueError("Freeze v4 chỉ chấp nhận early stopping source=dev")

    for method_id in (*candidate_list, published_reference, strongest_baseline):
        if method_id not in config.method_ids:
            raise ValueError(f"Method freeze không có trong config dev: {method_id}")
        spec = METHOD_SPECS.get(method_id)
        if spec is None or spec.status not in {"implemented", "derived", "evaluator_only"}:
            raise ValueError(f"Method freeze không runnable: {method_id}")
    for method_id in candidate_list:
        spec = METHOD_SPECS[method_id]
        if spec.role != "proposed" or not spec.confirmatory_allowed:
            raise ValueError(
                f"Candidate chưa được phép confirmatory theo registry/review: {method_id}"
            )

    commit = _git_commit(Path(__file__).resolve().parents[3])
    if commit is None:
        raise RuntimeError("Không đọc được Git commit để khóa freeze manifest")
    dataset_fingerprints = {
        dataset_id: dataset_fingerprint(config, dataset_id)
        for dataset_id in config.dataset_ids
    }
    split_hashes = {}
    feature_schema_hashes = {}
    for dataset_id in config.dataset_ids:
        root = config.paths.processed_root / dataset_id
        split_path = root / "split_manifest.json"
        feature_path = root / "feature_contract.json"
        if not split_path.exists() or not feature_path.exists():
            raise FileNotFoundError(
                f"Freeze v4 cần split_manifest.json và feature_contract.json: {root}"
            )
        split_hashes[dataset_id] = sha256_file(split_path)
        feature_schema_hashes[dataset_id] = sha256_file(feature_path)

    body = {
        "schema_version": 4,
        "previous_manifest_id": previous_manifest_id,
        "state": "M1_METHOD_FROZEN",
        "plan_version": plan_version,
        "review_hashes": REVIEW_HASHES,
        "code_commit": commit,
        "config_hash": protocol_hash(config),
        "confirmatory_config_hash": confirmatory_config_hash,
        "dataset_fingerprints": dataset_fingerprints,
        "split_hashes": split_hashes,
        "feature_schema_hashes": feature_schema_hashes,
        "selector_seeds": list(config.selector_seeds),
        "model_seed": config.model_seed,
        "rho_star": float(rho_star),
        "class_weight_policy": config.class_weight_policy,
        "learner_params": config.learner_params,
        "early_stopping_policy": config.early_stopping,
        "shard_policy": shard_policy,
        "method_roles": {
            "published_reference": published_reference,
            "strongest_baseline": strongest_baseline,
            "proposed_winner": selected_candidate,
        },
        "candidate_list": list(candidate_list),
        "selected_candidate": selected_candidate,
        "selection_evidence_hash": selection_evidence_hash,
        "stats_protocol_hash": stats_protocol_hash,
        "allowed_extensions": list(allowed_extensions),
        "test_access_policy": {
            "test_locked_until_manifest_valid": True,
            "confirmatory_unlocks_allowed": 1,
            "test_accessed_at_freeze": False,
        },
        "deviations": list(deviations),
    }
    manifest_id = stable_hash(body)
    output = config.paths.artifact_root / "freeze" / "freeze_manifest.json"
    if output.exists():
        raise FileExistsError(
            f"Freeze manifest đã tồn tại và bất biến: {output}; tạo deviation version riêng"
        )
    atomic_json(output, {**body, "manifest_id": manifest_id})
    return output


def validate_freeze_manifest_v4(
    manifest: dict,
    config: ExperimentConfig,
) -> None:
    """Validate manifest trước khi confirmatory runner được nhìn test."""
    required = {
        "schema_version", "manifest_id", "state", "plan_version", "review_hashes",
        "code_commit", "config_hash", "confirmatory_config_hash",
        "dataset_fingerprints", "split_hashes", "feature_schema_hashes",
        "selector_seeds", "model_seed", "rho_star", "class_weight_policy",
        "learner_params", "early_stopping_policy", "shard_policy", "method_roles",
        "candidate_list", "selected_candidate", "selection_evidence_hash",
        "stats_protocol_hash", "allowed_extensions", "test_access_policy", "deviations",
    }
    missing = required - set(manifest)
    if missing:
        raise RuntimeError(f"Freeze v4 thiếu trường: {sorted(missing)}")
    if manifest["schema_version"] != 4 or manifest["state"] != "M1_METHOD_FROZEN":
        raise RuntimeError("Confirmatory cần freeze schema v4 ở state M1_METHOD_FROZEN")
    body = {key: value for key, value in manifest.items() if key != "manifest_id"}
    if stable_hash(body) != manifest["manifest_id"]:
        raise RuntimeError("freeze manifest_id không khớp nội dung")
    if manifest["confirmatory_config_hash"] != protocol_hash(config):
        raise RuntimeError("Confirmatory config hash không khớp freeze v4")
    if manifest["review_hashes"] != REVIEW_HASHES:
        raise RuntimeError("Hash tài liệu review không khớp contract V2")
    current_commit = _git_commit(Path(__file__).resolve().parents[3])
    if current_commit is None or manifest["code_commit"] != current_commit:
        raise RuntimeError("Git commit hiện tại không khớp freeze v4")
    if tuple(manifest["selector_seeds"]) != tuple(config.selector_seeds):
        raise RuntimeError("selector_seeds không khớp freeze v4")
    if int(manifest["model_seed"]) != config.model_seed:
        raise RuntimeError("model_seed không khớp freeze v4")
    if manifest["class_weight_policy"] != config.class_weight_policy:
        raise RuntimeError("class_weight_policy không khớp freeze v4")
    if manifest["learner_params"] != config.learner_params:
        raise RuntimeError("learner_params không khớp freeze v4")
    if manifest["early_stopping_policy"] != config.early_stopping:
        raise RuntimeError("early_stopping policy không khớp freeze v4")
    policy = manifest["test_access_policy"]
    if policy.get("confirmatory_unlocks_allowed") != 1:
        raise RuntimeError("Freeze v4 phải khóa đúng một lần mở confirmatory test")
    candidates = manifest["candidate_list"]
    if not 1 <= len(candidates) <= 3 or len(set(candidates)) != len(candidates):
        raise RuntimeError("Freeze v4 phải có 1–3 candidate không trùng")
    if manifest["selected_candidate"] not in candidates:
        raise RuntimeError("Winner không nằm trong candidate_list đã freeze")
    if manifest["method_roles"].get("proposed_winner") != manifest["selected_candidate"]:
        raise RuntimeError("method_roles.proposed_winner không khớp winner đã freeze")
    for dataset_id in config.dataset_ids:
        if manifest["dataset_fingerprints"].get(dataset_id) != dataset_fingerprint(config, dataset_id):
            raise RuntimeError(f"Dataset fingerprint không khớp freeze: {dataset_id}")
        root = config.paths.processed_root / dataset_id
        expected_paths = {
            "split_hashes": root / "split_manifest.json",
            "feature_schema_hashes": root / "feature_contract.json",
        }
        for field, path in expected_paths.items():
            if not path.exists() or manifest[field].get(dataset_id) != sha256_file(path):
                raise RuntimeError(f"{field} không khớp freeze: {dataset_id}")
    for field in ("confirmatory_config_hash", "selection_evidence_hash", "stats_protocol_hash"):
        if not _is_sha256(str(manifest[field])):
            raise RuntimeError(f"{field} trong freeze v4 không phải SHA-256")


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdefABCDEF" for character in value)


def _git_commit(repository: Path) -> str | None:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repository,
        check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    )
    value = completed.stdout.strip()
    return value or None
