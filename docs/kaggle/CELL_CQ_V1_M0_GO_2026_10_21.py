# ============================================================
# CQ V1 — M0 EVIDENCE — KAGGLE T4 — DEV ONLY
# Commit pin: 6c1b336a8c43e9c5e6a757df48db4d3d538d29bd
# Không mở test metric; chỉ audit split metadata theo data card.
# Cell luôn sinh archive chẩn đoán, kể cả khi một bước sau đó lỗi.
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
EXPECTED_COMMIT = "6c1b336a8c43e9c5e6a757df48db4d3d538d29bd"
KAGGLE_DATASET = Path("/kaggle/input/datasets/hoangzyyng/cq-v1-phase-features-v2")
WORKING = Path("/kaggle/working")
REPO = WORKING / "skq_experiment"
SOURCE = WORKING / "cq_v1_source"
M0_DOCS = WORKING / "m0_docs" / "cq_v1"
LOG = WORKING / "cq_v1_m0_go.log"
STATUS = WORKING / "cq_v1_m0_execution_status.json"
ARCHIVE = WORKING / "skq_cq_v1_m0_evidence_2026_10_21.tar.gz"


execution = {
    "schema_version": 1,
    "started_utc": datetime.now(timezone.utc).isoformat(),
    "scope": "development_only_train_and_dev",
    "test_metrics_opened": False,
    "root_policy": "provisional_course_id",
    "confirmatory_eligible": False,
    "resource_calibration_scope": ["skq_pc", "skq_pc_lrq_sq", "skq_pc_r"],
    "steps": {},
}


def run(command, *, cwd=None, env=None):
    safe = [str(item) for item in command]
    print("$", " ".join(safe), flush=True)
    with LOG.open("a", encoding="utf-8") as stream:
        process = subprocess.Popen(
            safe, cwd=cwd, env=env, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            bufsize=1,
        )
        stream.write("$ " + " ".join(safe) + "\n")
        lines = []
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
            "status": "failed",
            "error_type": type(error).__name__,
            "error": str(error),
        }
        raise
    execution["steps"][name] = {"status": "success"}
    return value


def require_t4_compatible_gpu():
    output = run([
        "nvidia-smi", "--query-gpu=name,memory.total,driver_version",
        "--format=csv,noheader,nounits",
    ])
    rows = [line.strip() for line in output.splitlines() if line.strip()]
    if not rows:
        raise RuntimeError("Cell cấu hình XGBoost CUDA nhưng Kaggle chưa cấp GPU")
    execution["gpu_inventory"] = rows
    print("GPU được phát hiện:", rows)


def find_shortest(name):
    candidates = [path for path in KAGGLE_DATASET.rglob(name) if path.is_file()]
    if not candidates:
        raise FileNotFoundError(f"Không tìm thấy {name} dưới {KAGGLE_DATASET}")
    return min(candidates, key=lambda path: (len(path.parts), str(path)))


def build_unified_source():
    if SOURCE.exists():
        shutil.rmtree(SOURCE)
    (SOURCE / "model_ready").mkdir(parents=True)
    required_metadata = (
        "_SUCCESS.json", "validation.json", "feature_columns.json",
        "preprocessing.json", "run_manifest.json",
    )
    for name in required_metadata:
        shutil.copy2(find_shortest(name), SOURCE / name)
    summary_candidates = [
        path for path in KAGGLE_DATASET.rglob("summary.json") if path.is_file()
    ]
    if summary_candidates:
        source_summary = min(
            summary_candidates, key=lambda path: (len(path.parts), str(path)),
        )
        shutil.copy2(source_summary, SOURCE / "summary.json")
    phase_dirs = []
    for candidate in KAGGLE_DATASET.rglob("P1"):
        if candidate.is_dir() and all(
            (candidate / f"{split}.parquet").is_file()
            for split in ("train", "dev", "test")
        ):
            phase_dirs.append(candidate.parent)
    if not phase_dirs:
        raise FileNotFoundError("Không tìm thấy P1 có đủ train/dev/test")
    model_ready = min(phase_dirs, key=lambda path: (len(path.parts), str(path)))
    for phase in ("P1", "P2", "P3", "P4"):
        source_phase = model_ready / phase
        if not all(
            (source_phase / f"{split}.parquet").is_file()
            for split in ("train", "dev", "test")
        ):
            raise FileNotFoundError(f"Thiếu file ở {source_phase}")
        destination = SOURCE / "model_ready" / phase
        try:
            os.symlink(source_phase, destination, target_is_directory=True)
        except OSError:
            shutil.copytree(source_phase, destination)
    execution["resolved_data_root"] = str(model_ready)
    print("DATA_ROOT thống nhất:", SOURCE)


def audit_lr_convergence(experiment_ids):
    rows = []
    for experiment_id in experiment_ids:
        root = REPO / "artifacts" / "experiments" / experiment_id
        for cost_path in sorted(root.rglob("cost.json")):
            manifest_path = cost_path.parent / "manifest.json"
            if not manifest_path.is_file():
                continue
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("learner_id") != "lr":
                continue
            cost = json.loads(cost_path.read_text(encoding="utf-8"))
            rows.append({
                "experiment_id": experiment_id,
                "run_id": manifest.get("run_id"),
                "evaluation_split": manifest.get("evaluation_split"),
                "fit_converged": cost.get("fit_converged"),
                "optimizer_iterations": cost.get("optimizer_iterations"),
                "convergence_warnings": cost.get("convergence_warnings", []),
            })
    if not rows:
        raise RuntimeError("Không tìm thấy cost evidence của LR")
    summary = {
        "schema_version": 1,
        "all_lr_runs_converged": all(row["fit_converged"] is True for row in rows),
        "runs": rows,
    }
    output = M0_DOCS / "m0_lr_convergence.json"
    output.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    execution["lr_convergence"] = summary["all_lr_runs_converged"]
    if not summary["all_lr_runs_converged"]:
        print("CẢNH BÁO: ít nhất một LR chưa hội tụ; artifact đã ghi đầy đủ.")


def add_if_exists(tar, source, arcname):
    source = Path(source)
    if source.exists():
        tar.add(source, arcname=arcname)


def package_evidence():
    execution["finished_utc"] = datetime.now(timezone.utc).isoformat()
    STATUS.write_text(
        json.dumps(execution, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    if ARCHIVE.exists():
        ARCHIVE.unlink()
    with tarfile.open(ARCHIVE, "w:gz") as tar:
        add_if_exists(tar, REPO / "artifacts", "artifacts")
        add_if_exists(tar, M0_DOCS, "m0_docs/cq_v1")
        add_if_exists(tar, REPO / "configs" / "cq_v1_m0_fulltrain_b_dev_balanced_v1.json", "configs/cq_v1_m0_fulltrain_b_dev_balanced_v1.json")
        add_if_exists(tar, REPO / "configs" / "cq_v1_m0_fulltrain_b_dev_natural_v1.json", "configs/cq_v1_m0_fulltrain_b_dev_natural_v1.json")
        add_if_exists(tar, WORKING / "repository_commit_m0.txt", "repository_commit_m0.txt")
        add_if_exists(tar, STATUS, STATUS.name)
        add_if_exists(tar, LOG, LOG.name)
    print("\nArchive luôn được tạo:", ARCHIVE, flush=True)


LOG.write_text("CQ v1 M0 evidence — dev only\n", encoding="utf-8")
actual_commit = None
try:
    step("00_gpu_preflight", require_t4_compatible_gpu)

    def clone_and_pin():
        global actual_commit
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
        completed = subprocess.run(
            clone_command, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        print(completed.stdout or "", flush=True)
        if completed.returncode:
            raise RuntimeError("Clone repo thất bại")
        run(["git", "checkout", "--detach", EXPECTED_COMMIT], cwd=REPO)
        actual_commit = run(["git", "rev-parse", "HEAD"], cwd=REPO)
        if actual_commit != EXPECTED_COMMIT:
            raise RuntimeError(f"Sai commit: {actual_commit} != {EXPECTED_COMMIT}")
        (WORKING / "repository_commit_m0.txt").write_text(
            actual_commit + "\n", encoding="utf-8",
        )

    step("01_clone_and_pin", clone_and_pin)
    step("02_install", lambda: run([
        sys.executable, "-m", "pip", "install", "-q", "-e", f"{REPO}[boosting,dev]",
    ]))
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO / "src") + os.pathsep + str(REPO)
    M0_DOCS.mkdir(parents=True, exist_ok=True)
    pytest_files = (
        "tests/test_cq_protocol.py",
        "tests/test_cq_patch_1013_contracts.py",
        "tests/test_cq_m0_audit.py",
        "tests/test_feature_views.py",
        "tests/test_weights.py",
        "tests/test_headroom.py",
        "tests/test_cq_headroom_evidence.py",
        "tests/test_resource_calibration.py",
        "tests/test_freeze.py",
        "tests/test_freeze_v4.py",
        "tests/test_course_metrics.py",
        "tests/test_training_protocol.py",
        "tests/test_coretab_ova.py",
        "tests/test_cq_dev_endpoints.py",
    )
    execution["pytest_scope"] = list(pytest_files)
    step("02b_pytest_m0_contracts", lambda: run([
        sys.executable, "-m", "pytest", *pytest_files,
        "--junitxml", M0_DOCS / "pytest_m0_contracts.xml",
    ], cwd=REPO, env=env))
    step("03_resolve_dataset", build_unified_source)

    balanced = REPO / "configs" / "cq_v1_m0_fulltrain_b_dev_balanced_v1.json"
    natural = REPO / "configs" / "cq_v1_m0_fulltrain_b_dev_natural_v1.json"
    experiment_ids = (
        "cq_v1_m0_fulltrain_b_dev_balanced_v1",
        "cq_v1_m0_fulltrain_b_dev_natural_v1",
    )

    step("04_prepare_pool_b", lambda: run([
        sys.executable, "-m", "skq_exp.cli", "prepare-external",
        "--config", balanced, "--input-dir", SOURCE,
        "--dataset", "course_quality_v1", "--overwrite",
    ], cwd=REPO, env=env))

    probe_json = M0_DOCS / "m0_probes_dev_summary.json"
    step("05_run_m0_probes", lambda: run([
        sys.executable, REPO / "scripts" / "run_cq_v1_m0_probes.py",
        "--input-dir", SOURCE, "--output", probe_json,
    ], cwd=REPO, env=env))
    step("06_audit_m0", lambda: run([
        sys.executable, REPO / "scripts" / "audit_cq_v1_m0.py",
        "--input-dir", SOURCE, "--output-dir", M0_DOCS,
        "--root-policy", "pending", "--probe-evidence", probe_json,
    ], cwd=REPO, env=env))

    for policy, config in (("balanced", balanced), ("natural", natural)):
        step(f"07_fulltrain_b_{policy}", lambda config=config: run([
            sys.executable, "-m", "skq_exp.cli", "run",
            "--config", config, "--resume",
        ], cwd=REPO, env=env))

    step("08_audit_lr_convergence", lambda: audit_lr_convergence(experiment_ids))

    for experiment_id in experiment_ids:
        step(f"09_dev_endpoints_{experiment_id}", lambda experiment_id=experiment_id: run([
            sys.executable, REPO / "scripts" / "compute_cq_v1_dev_endpoints.py",
            "--input-dir", SOURCE,
            "--artifact-root", REPO / "artifacts",
            "--experiment-id", experiment_id,
            "--n-min", "30", "--root-policy", "provisional_course_id",
        ], cwd=REPO, env=env))

    # QĐ16 candidate subset đã đăng ký cho M0: 50k/200k/800k × 3.
    step("10_resource_calibration_candidates", lambda: run([
        sys.executable, REPO / "scripts" / "run_cq_v1_resource_calibration.py",
        "--processed-root", REPO / "data" / "processed",
        "--dataset", "course_quality_v1",
        "--output", REPO / "artifacts" / "cq_v1_m0_resource_calibration",
        "--budget-ratio", "0.02", "--max-threads", "4", "--replicates", "3",
        "--resume",
    ], cwd=REPO, env=env))

    execution["status"] = "success"
except Exception as error:
    execution["status"] = "failed"
    execution["fatal_error_type"] = type(error).__name__
    execution["fatal_error"] = str(error)
    with LOG.open("a", encoding="utf-8") as stream:
        stream.write("\nFATAL ERROR\n")
        stream.write(traceback.format_exc())
    print(traceback.format_exc(), flush=True)
    raise
finally:
    package_evidence()
    print("Commit:", actual_commit or "chưa clone/pin thành công")
    print("Trạng thái:", execution.get("status", "unknown"))
    print("Lưu ý: course_root vẫn provisional; test metric chưa được mở.")
