# ============================================================
# CQ V1 — M0 LR TUNING — MAX 8 CONFIGS — DEV ONLY — CPU
# FullTrain-B, natural/balanced; scaler luôn fit train-only.
# Cell không cần GPU và không đọc metric test.
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
EXPECTED_COMMIT = "f29ad5b79a8a257f094177afa72b936f530bac56"
KAGGLE_DATASET = Path("/kaggle/input/datasets/hoangzyyng/cq-v1-phase-features-v2")
WORKING = Path("/kaggle/working")
REPO = WORKING / "skq_experiment"
SOURCE = WORKING / "cq_v1_source"
LOG = WORKING / "cq_v1_m0_lr_tuning.log"
STATUS = WORKING / "cq_v1_m0_lr_tuning_status.json"
ARCHIVE = WORKING / "skq_cq_v1_m0_lr_tuning_max8_dev.tar.gz"
OUTPUT = REPO / "artifacts" / "cq_v1_m0_lr_tuning"
CONFIGS = tuple(
    f"cq_v1_m0_lr_tune_{index:02d}_{suffix}_v1.json"
    for index, suffix in (
        (1, "natural_lbfgs_c1"), (2, "natural_lbfgs_c01"),
        (3, "natural_newton_c1"), (4, "natural_newton_c01"),
        (5, "balanced_lbfgs_c1"), (6, "balanced_lbfgs_c01"),
        (7, "balanced_newton_c1"), (8, "balanced_newton_c01"),
    )
)

execution = {
    "schema_version": 1,
    "started_utc": datetime.now(timezone.utc).isoformat(),
    "scope": "M0_LR_tuning_max8_FullTrain_B_dev_only",
    "test_metrics_opened": False,
    "accelerator_policy": "CPU; LR does not benefit from Kaggle T4",
    "configs": list(CONFIGS),
    "steps": {},
}


def run(command, *, cwd=None, env=None):
    safe = [str(value) for value in command]
    print("$", " ".join(safe), flush=True)
    with LOG.open("a", encoding="utf-8") as stream:
        stream.write("$ " + " ".join(safe) + "\n")
        process = subprocess.Popen(
            safe, cwd=cwd, env=env, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1,
        )
        assert process.stdout is not None
        lines = []
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
            "status": "failed", "error_type": type(error).__name__, "error": str(error),
        }
        raise
    execution["steps"][name] = {"status": "success"}
    return value


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
    if commit != EXPECTED_COMMIT:
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
    roots = [
        path.parent for path in KAGGLE_DATASET.rglob("P1")
        if path.is_dir() and all((path / f"{split}.parquet").is_file() for split in ("train", "dev", "test"))
    ]
    if not roots:
        raise FileNotFoundError("Không tìm thấy model_ready/P1 đủ train/dev/test")
    model_ready = min(roots, key=lambda path: (len(path.parts), str(path)))
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
    STATUS.write_text(json.dumps(execution, ensure_ascii=False, indent=2), encoding="utf-8")
    if ARCHIVE.exists():
        ARCHIVE.unlink()
    with tarfile.open(ARCHIVE, "w:gz") as archive:
        for source, name in (
            (REPO / "artifacts", "artifacts"),
            (STATUS, STATUS.name), (LOG, LOG.name),
        ):
            if source.exists():
                archive.add(source, arcname=name)
        for config_name in CONFIGS:
            path = REPO / "configs" / config_name
            if path.exists():
                archive.add(path, arcname=f"configs/{config_name}")
    print("Archive:", ARCHIVE, flush=True)


LOG.write_text("CQ v1 M0 LR tuning — dev only, CPU\n", encoding="utf-8")
try:
    step("00_clone_and_pin", clone_and_pin)
    step("01_install", lambda: run([
        sys.executable, "-m", "pip", "install", "-q", "-e", f"{REPO}[dev]",
    ]))
    step("01a_prepare_output", lambda: OUTPUT.mkdir(parents=True, exist_ok=True))
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO / "src") + os.pathsep + str(REPO)
    step("02_contract_tests", lambda: run([
        sys.executable, "-m", "pytest",
        "tests/test_training_protocol.py", "tests/test_cq_dev_endpoints.py",
        "--junitxml", OUTPUT / "pytest_lr_tuning.xml",
    ], cwd=REPO, env=env))
    step("03_resolve_dataset", build_source)
    first_config = REPO / "configs" / CONFIGS[0]
    step("04_prepare_pool_b", lambda: run([
        sys.executable, "-m", "skq_exp.cli", "prepare-external",
        "--config", first_config, "--input-dir", SOURCE,
        "--dataset", "course_quality_v1", "--overwrite",
    ], cwd=REPO, env=env))
    for config_name in CONFIGS:
        config_path = REPO / "configs" / config_name
        experiment_id = config_name.removesuffix(".json")
        step(f"05_run_{experiment_id}", lambda config_path=config_path: run([
            sys.executable, "-m", "skq_exp.cli", "run",
            "--config", config_path, "--resume",
        ], cwd=REPO, env=env))
        step(f"06_endpoint_{experiment_id}", lambda experiment_id=experiment_id: run([
            sys.executable, REPO / "scripts" / "compute_cq_v1_dev_endpoints.py",
            "--input-dir", SOURCE, "--artifact-root", REPO / "artifacts",
            "--experiment-id", experiment_id, "--n-min", "30",
            "--root-policy", "provisional_course_id",
        ], cwd=REPO, env=env))
    decision_command = [
        sys.executable, REPO / "scripts" / "select_cq_v1_lr_config.py",
        "--output", OUTPUT / "lr_tuning_decision.json",
    ]
    for config_name in CONFIGS:
        decision_command.extend(["--config", REPO / "configs" / config_name])
    step("07_select_lr_config", lambda: run(decision_command, cwd=REPO, env=env))
    execution["status"] = "success"
except Exception as error:
    execution["status"] = "failed"
    execution["fatal_error_type"] = type(error).__name__
    execution["fatal_error"] = str(error)
    with LOG.open("a", encoding="utf-8") as stream:
        stream.write("\nFATAL ERROR\n" + traceback.format_exc())
    print(traceback.format_exc(), flush=True)
finally:
    package()
    print("Commit:", execution.get("repository_commit", "chưa clone/pin thành công"))
    print("Lưu ý: LR tuning dùng CPU; test metrics vẫn khóa.")
