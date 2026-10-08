"""Script này clone đúng repo/commit trong lock file vào external/repos.

Chạy một lần sau khi đưa project lên GitHub/Kaggle. Repo đã đúng commit được giữ
nguyên; thư mục sai remote hoặc sai commit sẽ dừng để người dùng kiểm tra thủ công.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
LOCK = json.loads((PROJECT / "external" / "official_repos.lock.json").read_text(encoding="utf-8"))
ROOT = PROJECT / "external" / "repos"


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    for name, entry in LOCK.items():
        target = ROOT / name
        if not target.exists():
            subprocess.run(["git", "clone", entry["url"], str(target)], check=True)
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=target, text=True).strip()
        if not commit.startswith(entry["commit_prefix"]):
            subprocess.run(["git", "fetch", "--all"], cwd=target, check=True)
            subprocess.run(["git", "checkout", entry["commit_prefix"]], cwd=target, check=True)
            commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=target, text=True).strip()
        if not commit.startswith(entry["commit_prefix"]):
            raise RuntimeError(f"{name}: commit {commit} không khớp lock")
        print(f"OK {name}: {commit}")


if __name__ == "__main__":
    main()
