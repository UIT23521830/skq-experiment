"""Tạo freeze manifest từ lựa chọn được khai báo rõ trước khi mở test.

Lệnh này không tự chọn winner. Người chạy phải truyền method/structure và lý do
freeze; với CQ có thể ghi rõ đây là cấu hình chuyển giao từ Adult. Cách này tránh
việc cell Kaggle tự viết JSON không kiểm tra fingerprint hoặc commit.
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

from ..artifacts import atomic_json
from ..config import ExperimentConfig
from ..methods import METHOD_SPECS
from .provenance import dataset_fingerprint, protocol_hash


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


def _git_commit(repository: Path) -> str | None:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repository,
        check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    )
    value = completed.stdout.strip()
    return value or None
