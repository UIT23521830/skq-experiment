# ============================================================
# CQ V1 — M0 HEADROOM QĐ12 — KAGGLE T4 — DEV ONLY
# Chạy 1 FullTrain-B + C02 tại 4 rho × 3 seed; không mở test.
# Cell luôn đóng gói log/evidence, kể cả khi một bước lỗi.
# ============================================================

import base64
import json
import os
import shutil
import subprocess
import sys
import tarfile
import traceback
from datetime import datetime, timezone
from pathlib import Path

from kaggle_secrets import UserSecretsClient


REPO_URL = "https://github.com/UIT23521830/skq-experiment.git"
BRANCH = "cq-v1-protocol-fixes"
EXPECTED_COMMIT = "38a190a"
KAGGLE_DATASET = Path("/kaggle/input/datasets/hoangzyyng/cq-v1-phase-features-v2")
WORKING = Path("/kaggle/working")
REPO = WORKING / "skq_experiment"
SOURCE = WORKING / "cq_v1_source"
LOG = WORKING / "cq_v1_m0_headroom.log"
STATUS = WORKING / "cq_v1_m0_headroom_status.json"
ARCHIVE = WORKING / "skq_cq_v1_m0_headroom_2026_10_21.tar.gz"

FULLTRAIN = "cq_v1_m0_fulltrain_b_dev_natural_xgb_v1.json"
C02_CONFIGS = (
    "cq_v1_m0_headroom_c02_rho005_natural_v1.json",
    "cq_v1_m0_headroom_c02_rho01_natural_v1.json",
    "cq_v1_m0_headroom_c02_rho02_natural_v1.json",
    "cq_v1_m0_headroom_c02_rho05_natural_v1.json",
)

execution = {
    "schema_version": 1,
    "started_utc": datetime.now(timezone.utc).isoformat(),
    "scope": "M0_QD12_development_only",
    "test_metrics_opened": False,
    "class_weight_policy": "natural_provisional_pending_supervisor_confirmation",
    "steps": {},
}


def run(command, *, cwd=None, env=None):
    safe = [str(value) for value in command]
    print("$", " ".join(safe), flush=True)
    lines = []
    with LOG.open("a", encoding="utf-8") as stream:
        stream.write("$ " + " ".join(safe) + "\n")
        process = subprocess.Popen(
            safe, cwd=cwd, env=env, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1,
        )
        assert process.stdout is not None
        for line in process.stdout:
            lines.append(line)
            stream.write(line)
            stream.flush()
            print(line, end="", flush=True)
        returncode = process.wait()
    if returncode:
        raise RuntimeError(f"Lệnh lỗi {returncode}: {safe[0]}")
    return "".join(lines).strip()


def step(name, function):
    print(f"\n=== {name} ===", flush=True)
    execution["steps"][name] = {"status": "running"}
    try:
        value = function()
    except Exception as error:
        execution["steps"][name] = {
            "status": "failed", "error_type": type(error).__name__,
            "error": str(error),
        }
        raise
    execution["steps"][name] = {"status": "success"}
    return value


def require_gpu():
    rows = run([
        "nvidia-smi", "--query-gpu=name,memory.total,driver_version",
        "--format=csv,noheader,nounits",
    ]).splitlines()
    if not rows:
        raise RuntimeError("XGB cấu hình CUDA nhưng Kaggle chưa cấp GPU")
    execution["gpu_inventory"] = rows


def clone_and_pin():
    token = UserSecretsClient().get_secret("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("Không đọc được Kaggle Secret GITHUB_TOKEN")
    if REPO.exists():
        shutil.rmtree(REPO)
    auth = base64.b64encode(f"x-access-token:{token}".encode()).decode()
    completed = subprocess.run([
        "git", "-c", f"http.extraHeader=Authorization: Basic {auth}",
        "clone", "--filter=blob:none", "--single-branch", "--branch", BRANCH,
        REPO_URL, str(REPO),
    ], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print(completed.stdout or "", flush=True)
    if completed.returncode:
        raise RuntimeError("Clone repo thất bại")
    run(["git", "checkout", "--detach", EXPECTED_COMMIT], cwd=REPO)
    commit = run(["git", "rev-parse", "HEAD"], cwd=REPO)
    if not commit.startswith(EXPECTED_COMMIT):
        raise RuntimeError(f"Sai commit: {commit} != {EXPECTED_COMMIT}")
    execution["repository_commit"] = commit


def shortest_file(name):
    paths = [path for path in KAGGLE_DATASET.rglob(name) if path.is_file()]
    if not paths:
        raise FileNotFoundError(f"Không tìm thấy {name}")
    return min(paths, key=lambda path: (len(path.parts), str(path)))


def build_source():
    if SOURCE.exists():
        shutil.rmtree(SOURCE)
    (SOURCE / "model_ready").mkdir(parents=True)
    for name in (
        "_SUCCESS.json", "validation.json", "feature_columns.json",
        "preprocessing.json", "run_manifest.json",
    ):
        shutil.copy2(shortest_file(name), SOURCE / name)
    phase_roots = [
        path.parent for path in KAGGLE_DATASET.rglob("P1")
        if path.is_dir() and all(
            (path / f"{split}.parquet").is_file()
            for split in ("train", "dev", "test")
        )
    ]
    if not phase_roots:
        raise FileNotFoundError("Không tìm thấy model_ready/P1 đủ ba split")
    model_ready = min(phase_roots, key=lambda path: (len(path.parts), str(path)))
    for phase in ("P1", "P2", "P3", "P4"):
        source_phase = model_ready / phase
        destination = SOURCE / "model_ready" / phase
        try:
            os.symlink(source_phase, destination, target_is_directory=True)
        except OSError:
            shutil.copytree(source_phase, destination)
    execution["resolved_data_root"] = str(model_ready)


def package():
    execution["finished_utc"] = datetime.now(timezone.utc).isoformat()
    STATUS.write_text(
        json.dumps(execution, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    if ARCHIVE.exists():
        ARCHIVE.unlink()
    with tarfile.open(ARCHIVE, "w:gz") as archive:
        for source, name in (
            (REPO / "artifacts", "artifacts"),
            (REPO / "configs" / FULLTRAIN, f"configs/{FULLTRAIN}"),
            (STATUS, STATUS.name), (LOG, LOG.name),
        ):
            if source.exists():
                archive.add(source, arcname=name)
        for name in C02_CONFIGS:
            source = REPO / "configs" / name
            if source.exists():
                archive.add(source, arcname=f"configs/{name}")
    print("Archive:", ARCHIVE, flush=True)


LOG.write_text("CQ v1 M0 headroom QĐ12 — dev only\n", encoding="utf-8")
try:
    step("00_gpu_preflight", require_gpu)
    step("01_clone_and_pin", clone_and_pin)
    step("02_install", lambda: run([
        sys.executable, "-m", "pip", "install", "-q", "-e", f"{REPO}[boosting]",
    ]))
    step("03_resolve_dataset", build_source)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO / "src") + os.pathsep + str(REPO)
    fulltrain_path = REPO / "configs" / FULLTRAIN
    step("04_prepare_pool_b", lambda: run([
        sys.executable, "-m", "skq_exp.cli", "prepare-external",
        "--config", fulltrain_path, "--input-dir", SOURCE,
        "--dataset", "course_quality_v1", "--overwrite",
    ], cwd=REPO, env=env))
    step("05_fulltrain_b_natural_xgb", lambda: run([
        sys.executable, "-m", "skq_exp.cli", "run",
        "--config", fulltrain_path, "--resume",
    ], cwd=REPO, env=env))
    for index, name in enumerate(C02_CONFIGS, start=1):
        step(f"06_c02_{index}_{name}", lambda name=name: run([
            sys.executable, "-m", "skq_exp.cli", "run",
            "--config", REPO / "configs" / name, "--resume",
        ], cwd=REPO, env=env))
    command = [
        sys.executable, REPO / "scripts" / "compute_cq_v1_headroom.py",
        "--artifact-root", REPO / "artifacts",
        "--fulltrain-config", fulltrain_path,
        "--output", REPO / "artifacts" / "cq_v1_m0_headroom" / "headroom_decision.json",
    ]
    for name in C02_CONFIGS:
        command.extend(["--c02-config", REPO / "configs" / name])
    step("07_compute_headroom_decision", lambda: run(command, cwd=REPO, env=env))
    execution["status"] = "success"
except Exception as error:
    execution["status"] = "failed"
    execution["fatal_error_type"] = type(error).__name__
    execution["fatal_error"] = str(error)
    with LOG.open("a", encoding="utf-8") as stream:
        stream.write("\nFATAL ERROR\n" + traceback.format_exc())
    print(traceback.format_exc(), flush=True)
    raise
finally:
    package()
    print("Test metric chưa được mở; natural policy vẫn chờ giảng viên xác nhận.")
