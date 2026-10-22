# ============================================================
# CQ V1 — M0 QĐ16 — 10 FIXED SELECTORS + 3 CANDIDATES
# Kaggle T4, train-only calibration at rho* read from headroom evidence.
# Chạy từng method riêng để checkpoint/resume; luôn đóng gói archive cuối.
# ============================================================

import base64
import hashlib
import json
import os
import signal
import shutil
import subprocess
import sys
import tarfile
import threading
import time
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
LOG = WORKING / "cq_v1_m0_qd16_resource.log"
STATUS = WORKING / "cq_v1_m0_qd16_resource_status.json"
ARCHIVE = WORKING / "skq_cq_v1_m0_qd16_resource_rhostar.tar.gz"
# Đặt checkpoint ngoài repo để clone lại cell không xóa tiến độ đo nhiều giờ.
OUTPUT = WORKING / "cq_v1_m0_resource_calibration_rhostar"
HEADROOM = REPO / "docs" / "cq_v1" / "m0_headroom_decision_2026_10_21.json"
PRIOR_ARCHIVE_NAME = "skq_cq_v1_m0_qd16_resource_rhostar.tar.gz"
PRIOR_ARCHIVE_SHA256 = "83BEAA285714AB642B722DFDC9E816B38193833D9FB44F73E39E17218D04ECAA"
# Đây là trần an toàn cho toàn lệnh calibration Kernel Thinning, không được ghi
# thành một run success. Khi hết giờ, cell giữ checkpoint rồi chạy tiếp method sau.
KERNEL_CALIBRATION_TIMEOUT_SECONDS = 3 * 60 * 60

METHODS = (
    "c01_uniform_random", "c02_stratified_random", "c03_phase_class_random",
    "a_coretab_xgb_ova", "n_bdis_native", "n_gcoreset_benchmark",
    "b_moderate_ds_adapted", "b_ccs_oof_xgb_adapted",
    "b_dataoob_official", "b_kernel_thinning_classwise",
    "skq_pc", "skq_pc_lrq_sq", "skq_pc_r",
)
UPSTREAM_REPOS = (
    "coretab", "bdis", "tabular_data_distillation", "moderate_ds",
    "ccs", "dataoob", "goodpoints",
)

execution = {
    "schema_version": 1,
    "started_utc": datetime.now(timezone.utc).isoformat(),
    "scope": "M0_QD16_10_fixed_plus_3_candidates_train_only",
    "test_metrics_opened": False,
    "methods": list(METHODS),
    "steps": {},
}


class CommandTimeout(RuntimeError):
    """Lệnh con vượt trần notebook và đã bị kết thúc cùng process tree."""


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def terminate_process_group(process):
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=15)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=15)


def run(command, *, cwd=None, env=None, timeout_seconds=None):
    safe = [str(value) for value in command]
    print("$", " ".join(safe), flush=True)
    started = time.monotonic()
    with LOG.open("a", encoding="utf-8") as stream:
        stream.write("$ " + " ".join(safe) + "\n")
        process = subprocess.Popen(
            safe, cwd=cwd, env=env, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1,
            start_new_session=True,
        )
        assert process.stdout is not None
        lines = []
        def pump_output():
            for line in process.stdout:
                lines.append(line)
                stream.write(line)
                stream.flush()
                print(line, end="", flush=True)

        reader = threading.Thread(target=pump_output, daemon=True)
        reader.start()
        try:
            returncode = process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired as error:
            terminate_process_group(process)
            reader.join(timeout=30)
            elapsed = time.monotonic() - started
            marker = (
                f"COMMAND_TIMEOUT seconds={elapsed:.3f} "
                f"limit={timeout_seconds} command={safe[0]}\n"
            )
            stream.write(marker)
            stream.flush()
            print(marker, end="", flush=True)
            raise CommandTimeout(marker.strip()) from error
        reader.join(timeout=30)
    if returncode:
        raise RuntimeError(f"Lệnh lỗi {returncode}: {safe[0]}")
    return "".join(lines).strip()


def restore_prior_checkpoint():
    """Khôi phục archive đã kiểm kê; không trộn archive lạ hoặc sai checksum."""
    summary = OUTPUT / "resource_decision_all.json"
    if summary.is_file():
        execution["prior_checkpoint"] = {"mode": "existing_working_directory"}
        return
    candidates = sorted(
        Path("/kaggle/input").rglob(PRIOR_ARCHIVE_NAME),
        key=lambda path: (len(path.parts), str(path)),
    )
    matching = [path for path in candidates if sha256_file(path) == PRIOR_ARCHIVE_SHA256]
    if not matching:
        execution["prior_checkpoint"] = {
            "mode": "not_found",
            "expected_name": PRIOR_ARCHIVE_NAME,
            "expected_sha256": PRIOR_ARCHIVE_SHA256,
        }
        OUTPUT.mkdir(parents=True, exist_ok=True)
        return
    source_archive = matching[0]
    restore_root = WORKING / "qd16_prior_restore"
    if restore_root.exists():
        shutil.rmtree(restore_root)
    restore_root.mkdir(parents=True)
    with tarfile.open(source_archive, "r:gz") as archive:
        archive.extractall(restore_root, filter="data")
    source_output = restore_root / "artifacts" / "cq_v1_m0_resource_calibration_rhostar"
    if not (source_output / "resource_decision_all.json").is_file():
        raise RuntimeError("Archive prior không chứa resource_decision_all.json")
    shutil.copytree(source_output, OUTPUT, dirs_exist_ok=True)
    payload = json.loads((OUTPUT / "resource_decision_all.json").read_text(encoding="utf-8"))
    if float(payload.get("budget_ratio", -1)) != 0.005:
        raise RuntimeError("Archive prior không dùng rho*=0.005")
    execution["prior_checkpoint"] = {
        "mode": "restored_archive",
        "path": str(source_archive),
        "sha256": PRIOR_ARCHIVE_SHA256,
        "measured_method_count": int(payload.get("measured_method_count", 0)),
    }


def completed_methods():
    summary = OUTPUT / "resource_decision_all.json"
    if not summary.is_file():
        return set()
    payload = json.loads(summary.read_text(encoding="utf-8"))
    completed = set()
    for method_id, item in payload.get("methods", {}).items():
        fit = item.get("fit", {})
        counts = fit.get("replicate_counts", {})
        if fit.get("fit_status") == "fitted" and all(
            int(counts.get(str(rows), 0)) == 3 for rows in (50_000, 200_000, 800_000)
        ):
            completed.add(method_id)
    return completed


def write_censored_record(method_id, timeout_seconds):
    checkpoint = OUTPUT / f"observations_{method_id}.json"
    observations = []
    if checkpoint.is_file():
        observations = json.loads(checkpoint.read_text(encoding="utf-8"))
    counts = {}
    for item in observations:
        key = str(item.get("rows"))
        counts[key] = counts.get(key, 0) + 1
    record = {
        "schema_version": 1,
        "method_id": method_id,
        "status": "calibration_timeout_censored",
        "is_success": False,
        "timeout_seconds": timeout_seconds,
        "completed_observation_count": len(observations),
        "replicate_counts": counts,
        "action": "preserve_failure_and_continue_remaining_panel",
        "interpretation": (
            "Không fit scaling model và không thay bằng proxy; cần ghi TIMEOUT/CENSORED "
            "trong bảng QĐ16 hoặc xin protocol resolution."
        ),
    }
    target = OUTPUT / f"resource_censor_{method_id}.json"
    target.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return record


def step(name, function, *, continue_on_error=False):
    print(f"\n=== {name} ===", flush=True)
    execution["steps"][name] = {"status": "running"}
    try:
        value = function()
    except Exception as error:
        execution["steps"][name] = {
            "status": "failed", "error_type": type(error).__name__, "error": str(error),
        }
        if continue_on_error:
            print(traceback.format_exc(), flush=True)
            return None
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


def require_gpu():
    rows = run([
        "nvidia-smi", "--query-gpu=name,memory.total,driver_version",
        "--format=csv,noheader,nounits",
    ]).splitlines()
    if not rows:
        raise RuntimeError("QĐ16 đã đăng ký Kaggle T4 nhưng runtime chưa cấp GPU")
    execution["gpu_inventory"] = rows


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
    completed = [
        name for name, item in execution["steps"].items()
        if name.startswith("07_calibrate_")
        and item.get("status") in {"success", "reused_complete"}
    ]
    execution["completed_calibration_methods"] = len(completed)
    if len(completed) < len(METHODS):
        execution["status"] = "checkpoint_in_progress"
    elif all(item["status"] == "success" for item in execution["steps"].values()):
        execution["status"] = "success"
    else:
        execution["status"] = "partial_or_failed"
    STATUS.write_text(json.dumps(execution, ensure_ascii=False, indent=2), encoding="utf-8")
    if ARCHIVE.exists():
        ARCHIVE.unlink()
    with tarfile.open(ARCHIVE, "w:gz") as archive:
        for source, name in (
            (OUTPUT, "artifacts/cq_v1_m0_resource_calibration_rhostar"),
            (HEADROOM, "evidence/m0_headroom_decision_2026_10_21.json"),
            (STATUS, STATUS.name), (LOG, LOG.name),
        ):
            if source.exists():
                archive.add(source, arcname=name)
    print("Archive:", ARCHIVE, flush=True)


LOG.write_text("CQ v1 M0 QĐ16 — train-only resource calibration\n", encoding="utf-8")
try:
    step("00_gpu_preflight", require_gpu)
    step("00a_restore_prior_checkpoint", restore_prior_checkpoint)
    step("01_clone_and_pin", clone_and_pin)
    step("02_install", lambda: run([
        sys.executable, "-m", "pip", "install", "-q", "-e", f"{REPO}[kaggle-panel,dev]",
    ]))
    step("02a_prepare_output", lambda: OUTPUT.mkdir(parents=True, exist_ok=True))
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO / "src") + os.pathsep + str(REPO)
    step("03_contract_tests", lambda: run([
        sys.executable, "-m", "pytest",
        "tests/test_resource_calibration.py", "tests/test_resource_schedule.py",
        "tests/test_modern_baselines.py", "tests/test_coretab_ova.py",
        "--junitxml", OUTPUT / "pytest_qd16.xml",
    ], cwd=REPO, env=env))
    step("04_resolve_dataset", build_source)
    prepare_config = REPO / "configs" / "cq_v1_m0_fulltrain_b_dev_balanced_v1.json"
    step("05_prepare_pool_b", lambda: run([
        sys.executable, "-m", "skq_exp.cli", "prepare-external",
        "--config", prepare_config, "--input-dir", SOURCE,
        "--dataset", "course_quality_v1", "--overwrite",
    ], cwd=REPO, env=env))
    fetch_command = [sys.executable, REPO / "scripts" / "fetch_official_repos.py"]
    for repo_name in UPSTREAM_REPOS:
        fetch_command.extend(["--repo", repo_name])
    step("06_fetch_locked_upstreams", lambda: run(fetch_command, cwd=REPO, env=env))
    reusable = completed_methods()
    execution["reused_complete_methods"] = sorted(reusable)
    for method_id in METHODS:
        step_name = f"07_calibrate_{method_id}"
        if method_id in reusable:
            execution["steps"][step_name] = {
                "status": "reused_complete",
                "source": execution.get("prior_checkpoint", {}).get("mode"),
            }
            print(f"\n=== {step_name} ===\nREUSE_COMPLETE method={method_id}", flush=True)
            package()
            continue
        command = [
            sys.executable, REPO / "scripts" / "run_cq_v1_resource_calibration.py",
            "--processed-root", REPO / "data" / "processed",
            "--dataset", "course_quality_v1", "--output", OUTPUT,
            "--headroom-decision", HEADROOM,
            "--external-root", REPO / "external" / "repos",
            "--max-threads", "4", "--replicates", "3", "--resume",
            "--method", method_id,
        ]
        timeout_seconds = (
            KERNEL_CALIBRATION_TIMEOUT_SECONDS
            if method_id == "b_kernel_thinning_classwise" else None
        )
        step(
            step_name,
            lambda command=command, timeout_seconds=timeout_seconds: run(
                command, cwd=REPO, env=env, timeout_seconds=timeout_seconds,
            ),
            continue_on_error=True,
        )
        if execution["steps"][step_name].get("error_type") == "CommandTimeout":
            execution["steps"][step_name]["censored_evidence"] = write_censored_record(
                method_id, timeout_seconds,
            )
        # Archive sau từng method để Save Version/phiên bị ngắt vẫn còn checkpoint.
        package()
    decision = OUTPUT / "resource_decision_all.json"
    step("08_compute_selector_schedule", lambda: run([
        sys.executable, REPO / "scripts" / "compute_cq_v1_resource_schedule.py",
        "--calibration", decision,
        "--output", OUTPUT / "resource_schedule_selector_only.json",
    ], cwd=REPO, env=env), continue_on_error=True)
except Exception as error:
    execution["fatal_error_type"] = type(error).__name__
    execution["fatal_error"] = str(error)
    with LOG.open("a", encoding="utf-8") as stream:
        stream.write("\nFATAL ERROR\n" + traceback.format_exc())
    print(traceback.format_exc(), flush=True)
finally:
    package()
    print("Commit:", execution.get("repository_commit", "chưa clone/pin thành công"))
    print("Lưu ý: rho* được đọc từ headroom dev; cell không mở test metrics.")
