"""File này cung cấp thao tác chung cho adapter repo ngoài.

Nó kiểm tra vị trí repo, lấy commit Git và quản lý sys.path tạm thời. Mục đích là
giữ provenance rõ mà không cài code repo ngoài vào package SKQ.
"""

from __future__ import annotations

import contextlib
import subprocess
import sys
from pathlib import Path


def git_commit(repo: Path) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo, text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return None


@contextlib.contextmanager
def prepend_sys_path(path: Path):
    old = list(sys.path)
    sys.path.insert(0, str(path))
    try:
        yield
    finally:
        sys.path[:] = old
