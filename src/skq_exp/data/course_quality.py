"""Alias tương thích cho code/cell CourseQuality đã phát hành trước đây.

Code mới nên gọi ``prepare_external_dataset(dataset_id, ...)``. Alias này được
giữ để notebook cũ không hỏng khi project chuyển sang registry adapter chung.
"""

from __future__ import annotations

from pathlib import Path

from .adapters.registry import prepare_external_dataset


DATASET_ID = "course_quality_med_v1"


def prepare_course_quality_snapshot(
    input_dir: str | Path,
    processed_root: str | Path,
    *,
    dataset_id: str = DATASET_ID,
    overwrite: bool = False,
    validate_expected_rows: bool = True,
) -> Path:
    return prepare_external_dataset(
        dataset_id,
        input_dir,
        processed_root,
        overwrite=overwrite,
        validate_expected_rows=validate_expected_rows,
    )
