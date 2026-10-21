# ============================================================
# CQ V1 — M0 GO EVIDENCE — KAGGLE T4 — DEV ONLY
# Commit pin: e9b60aad6b832dcb0469bf652a5aa5810d024496
# Không mở test metric; chỉ audit split metadata theo data card.
# ============================================================

import base64
import json
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

from kaggle_secrets import UserSecretsClient


REPO_URL = "https://github.com/UIT23521830/skq-experiment.git"
BRANCH = "cq-v1-protocol-fixes"
EXPECTED_COMMIT = "e9b60aad6b832dcb0469bf652a5aa5810d024496"
KAGGLE_DATASET = Path("/kaggle/input/datasets/hoangzyyng/cq-v1-phase-features-v2")
WORKING = Path("/kaggle/working")
REPO = WORKING / "skq_experiment"
SOURCE = WORKING / "cq_v1_source"
M0_DOCS = WORKING / "m0_docs" / "cq_v1"
LOG = WORKING / "cq_v1_m0_go.log"
ARCHIVE = WORKING / "skq_cq_v1_m0_go_dev_only_2026_10_21.tar.gz"


def run(command, *, cwd=None, env=None):
    safe = [str(item) for item in command]
    print("$", " ".join(safe), flush=True)
    with LOG.open("a", encoding="utf-8") as stream:
        completed = subprocess.run(
            safe, cwd=cwd, env=env, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        stream.write("$ " + " ".join(safe) + "\n")
        stream.write(completed.stdout or "")
        print(completed.stdout or "", flush=True)
    if completed.returncode:
        raise RuntimeError(f"Lệnh lỗi {completed.returncode}: {safe[0]}")
    return (completed.stdout or "").strip()


def find_shortest(name):
    candidates = [path for path in KAGGLE_DATASET.rglob(name) if path.is_file()]
    if not candidates:
        raise FileNotFoundError(f"Không tìm thấy {name} dưới {KAGGLE_DATASET}")
    return min(candidates, key=lambda path: (len(path.parts), str(path)))


def build_unified_source():
    if SOURCE.exists():
        shutil.rmtree(SOURCE)
    (SOURCE / "model_ready").mkdir(parents=True)
    for name in ("_SUCCESS.json", "validation.json", "feature_columns.json", "preprocessing.json", "run_manifest.json"):
        source_file = find_shortest(name)
        shutil.copy2(source_file, SOURCE / name)
    summary_candidates = [path for path in KAGGLE_DATASET.rglob("summary.json") if path.is_file()]
    if summary_candidates:
        shutil.copy2(min(summary_candidates, key=lambda path: (len(path.parts), str(path))), SOURCE / "summary.json")
    phase_dirs = []
    for candidate in KAGGLE_DATASET.rglob("P1"):
        if candidate.is_dir() and all((candidate / f"{split}.parquet").is_file() for split in ("train", "dev", "test")):
            phase_dirs.append(candidate.parent)
    if not phase_dirs:
        raise FileNotFoundError("Không tìm thấy model_ready/P1 có đủ train/dev/test")
    model_ready = min(phase_dirs, key=lambda path: (len(path.parts), str(path)))
    for phase in ("P1", "P2", "P3", "P4"):
        source_phase = model_ready / phase
        if not all((source_phase / f"{split}.parquet").is_file() for split in ("train", "dev", "test")):
            raise FileNotFoundError(f"Thiếu file ở {source_phase}")
        destination = SOURCE / "model_ready" / phase
        try:
            os.symlink(source_phase, destination, target_is_directory=True)
        except OSError:
            shutil.copytree(source_phase, destination)
    print("DATA_ROOT thống nhất:", SOURCE)


LOG.write_text("CQ v1 M0 GO — dev only\n", encoding="utf-8")
token = UserSecretsClient().get_secret("GITHUB_TOKEN")
if not token:
    raise RuntimeError("Không đọc được Kaggle Secret GITHUB_TOKEN")
if REPO.exists():
    shutil.rmtree(REPO)
auth = base64.b64encode(f"x-access-token:{token}".encode()).decode()
clone_command = [
    "git", "-c", f"http.extraHeader=Authorization: Basic {auth}",
    "clone", "--filter=blob:none", "--single-branch", "--branch", BRANCH,
    REPO_URL, str(REPO),
]
# Không ghi clone_command vào log vì chứa credential mã hóa.
completed = subprocess.run(clone_command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
print(completed.stdout or "", flush=True)
if completed.returncode:
    raise RuntimeError("Clone repo thất bại")
run(["git", "checkout", "--detach", EXPECTED_COMMIT], cwd=REPO)
actual_commit = run(["git", "rev-parse", "HEAD"], cwd=REPO)
if actual_commit != EXPECTED_COMMIT:
    raise RuntimeError(f"Sai commit: {actual_commit} != {EXPECTED_COMMIT}")
(WORKING / "repository_commit_m0.txt").write_text(actual_commit + "\n", encoding="utf-8")

run([sys.executable, "-m", "pip", "install", "-q", "-e", f"{REPO}[boosting]"])
build_unified_source()

env = os.environ.copy()
env["PYTHONPATH"] = str(REPO / "src") + os.pathsep + str(REPO)
balanced = REPO / "configs" / "cq_v1_m0_fulltrain_b_dev_balanced_v1.json"
natural = REPO / "configs" / "cq_v1_m0_fulltrain_b_dev_natural_v1.json"

# 1) Chuẩn bị Pool B; adapter có audit test metadata nhưng mọi run bên dưới chỉ dev.
run([
    sys.executable, "-m", "skq_exp.cli", "prepare-external",
    "--config", balanced, "--input-dir", SOURCE,
    "--dataset", "course_quality_v1", "--overwrite",
], cwd=REPO, env=env)

# 2) D02/D04/D05 và data card M0. D03/D06 giữ BLOCKED nếu thiếu raw source.
M0_DOCS.mkdir(parents=True, exist_ok=True)
probe_json = M0_DOCS / "m0_probes_dev_summary.json"
run([
    sys.executable, REPO / "scripts" / "run_cq_v1_m0_probes.py",
    "--input-dir", SOURCE, "--output", probe_json,
], cwd=REPO, env=env)
run([
    sys.executable, REPO / "scripts" / "audit_cq_v1_m0.py",
    "--input-dir", SOURCE, "--output-dir", M0_DOCS,
    "--root-policy", "pending", "--probe-evidence", probe_json,
], cwd=REPO, env=env)

# 3) FullTrain-B: LR/XGB × balanced/natural; test_locked=true trong cả hai config.
for config in (balanced, natural):
    run([
        sys.executable, "-m", "skq_exp.cli", "run",
        "--config", config, "--resume",
    ], cwd=REPO, env=env)

# 4) UL/EC dev provisional theo course_id. Không đổi thành confirmatory nếu chưa có xác nhận root.
for experiment_id in (
    "cq_v1_m0_fulltrain_b_dev_balanced_v1",
    "cq_v1_m0_fulltrain_b_dev_natural_v1",
):
    run([
        sys.executable, REPO / "scripts" / "compute_cq_v1_dev_endpoints.py",
        "--input-dir", SOURCE,
        "--artifact-root", REPO / "artifacts",
        "--experiment-id", experiment_id,
        "--n-min", "30", "--root-policy", "provisional_course_id",
    ], cwd=REPO, env=env)

# 5) QĐ16: 50k/200k/800k × 3 cho ba candidate, target là toàn Pool B train.
run([
    sys.executable, REPO / "scripts" / "run_cq_v1_resource_calibration.py",
    "--processed-root", REPO / "data" / "processed",
    "--dataset", "course_quality_v1",
    "--output", REPO / "artifacts" / "cq_v1_m0_resource_calibration",
    "--budget-ratio", "0.02", "--max-threads", "4", "--replicates", "3",
], cwd=REPO, env=env)

# 6) Đóng gói evidence; không đóng gói source Parquet hay token.
if ARCHIVE.exists():
    ARCHIVE.unlink()
with tarfile.open(ARCHIVE, "w:gz") as tar:
    tar.add(REPO / "artifacts", arcname="artifacts")
    tar.add(M0_DOCS, arcname="m0_docs/cq_v1")
    tar.add(REPO / "configs" / balanced.name, arcname=f"configs/{balanced.name}")
    tar.add(REPO / "configs" / natural.name, arcname=f"configs/{natural.name}")
    tar.add(WORKING / "repository_commit_m0.txt", arcname="repository_commit_m0.txt")
    tar.add(LOG, arcname="cq_v1_m0_go.log")

print("\nHOÀN TẤT DEV-ONLY M0 EVIDENCE")
print("Commit:", actual_commit)
print("Archive:", ARCHIVE)
print("Lưu ý: course_root vẫn provisional; test metric chưa được mở.")
