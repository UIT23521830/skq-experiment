"""Kiểm các hàm lõi của audit M0, không đọc dữ liệu CQ riêng tư."""

from __future__ import annotations

import pandas as pd

from scripts.audit_cq_v1_m0 import _hash_rows, _quality_class


def test_quality_class_keeps_registered_boundaries() -> None:
    values = pd.Series([0.0, 0.1999, 0.2, 0.3999, 0.4, 1.0])
    assert _quality_class(values).tolist() == ["E", "E", "G", "G", "A", "A"]


def test_public_split_hash_is_order_invariant() -> None:
    frame = pd.DataFrame({"course_id": [2, 1], "split": ["test", "train"]})
    assert _hash_rows(frame) == _hash_rows(frame.iloc[::-1])
