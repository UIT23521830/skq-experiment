# ============================================================
# CQ V3 — M0 CONDITIONAL-GO PACKET — KAGGLE T4 — DEV ONLY
# Pin code commit: 81e1181a8ca25b0dceb9c387a3e3811a6f2d3466
# Input is the private cq_v3_m0_dev bundle; no test parquet is permitted.
# Runs mandatory M0 probes, FullTrain-B policies and QD12 headroom only.
# Always creates a diagnostic archive, including after a failed step.
# ============================================================

import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import traceback
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from kaggle_secrets import UserSecretsClient


REPO_URL = "https://github.com/UIT23521830/skq-experiment.git"
BRANCH = "cq-v1-protocol-fixes"
EXPECTED_COMMIT = "81e1181a8ca25b0dceb9c387a3e3811a6f2d3466"
EXPECTED_BUNDLE_ZIP_SHA256 = "9f60946c140b7e16ee1f9bb3d94fc21bbec898f476be669416ebd6e4c55995a6"
WORKING = Path("/kaggle/working")
REPO = WORKING / "skq_experiment"
SOURCE = WORKING / "cq_v3_m0_source"
M0_DOCS = WORKING / "m0_docs" / "cq_v3"
LOG = WORKING / "cq_v3_m0_go.log"
STATUS = WORKING / "cq_v3_m0_execution_status.json"
ARCHIVE = WORKING / "skq_cq_v3_m0_conditional_go_2026_10_21.tar.gz"

FULLTRAIN_CONFIGS = (
    "cq_v3_m0_fulltrain_b_dev_balanced_v1.json",
    "cq_v3_m0_fulltrain_b_dev_natural_v1.json",
)
HEADROOM_FULLTRAIN = "cq_v3_m0_fulltrain_b_dev_natural_xgb_v1.json"
HEADROOM_C02 = (
    "cq_v3_m0_headroom_c02_rho005_natural_v1.json",
    "cq_v3_m0_headroom_c02_rho01_natural_v1.json",
    "cq_v3_m0_headroom_c02_rho02_natural_v1.json",
    "cq_v3_m0_headroom_c02_rho05_natural_v1.json",
)

execution = {
    "schema_version": 1,
    "started_utc": datetime.now(timezone.utc).isoformat(),
    "scope": "CQ_V3_M0_train_dev_only",
    "test_files_permitted": False,
    "test_metrics_opened": False,
    "split_policy": "course_random_pending_lecturer_approval",
    "root_policy": "provisional_course_id_pending_written_confirmation",
    "fulltrain_a_status": "blocked_not_in_source_bundle",
    "steps": {},
}


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().lower()


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
            "status": "failed",
            "error_type": type(error).__name__,
            "error": str(error),
        }
        raise
    execution["steps"][name] = {"status": "success"}
    return value


def require_t4():
    rows = run([
        "nvidia-smi", "--query-gpu=name,memory.total,driver_version",
        "--format=csv,noheader,nounits",
    ]).splitlines()
    if not rows or not any("T4" in row for row in rows):
        raise RuntimeError("Cell XGBoost CUDA cần Kaggle GPU T4")
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
    actual = run(["git", "rev-parse", "HEAD"], cwd=REPO)
    if actual != EXPECTED_COMMIT:
        raise RuntimeError(f"Sai commit: {actual} != {EXPECTED_COMMIT}")
    execution["repository_commit"] = actual
    (WORKING / "repository_commit_cq_v3_m0.txt").write_text(
        actual + "\n", encoding="utf-8",
    )


def _valid_bundle_root(path):
    return (
        (path / "BUNDLE_MANIFEST.json").is_file()
        and (path / "supervised_raw" / "P1" / "train.parquet").is_file()
        and (path / "supervised_raw" / "P4" / "dev.parquet").is_file()
    )


def resolve_private_bundle():
    candidates = sorted(
        {path.parent for path in Path("/kaggle/input").rglob("BUNDLE_MANIFEST.json") if _valid_bundle_root(path.parent)},
        key=lambda path: (len(path.parts), str(path)),
    )
    if not candidates:
        zip_candidates = sorted(Path("/kaggle/input").rglob("cq_v3_m0_dev.zip"))
        if len(zip_candidates) != 1:
            raise FileNotFoundError(
                "Cần đúng một cq_v3_m0_dev bundle hoặc cq_v3_m0_dev.zip trong Kaggle Input"
            )
        archive = zip_candidates[0]
        if sha256_file(archive) != EXPECTED_BUNDLE_ZIP_SHA256:
            raise RuntimeError("SHA-256 gói cq_v3_m0_dev.zip không khớp")
        unpacked = WORKING / "cq_v3_m0_unpacked"
        if unpacked.exists():
            shutil.rmtree(unpacked)
        unpacked.mkdir()
        with zipfile.ZipFile(archive) as zipped:
            zipped.extractall(unpacked)
        candidates = [path.parent for path in unpacked.rglob("BUNDLE_MANIFEST.json") if _valid_bundle_root(path.parent)]
    if len(candidates) != 1:
        raise RuntimeError(f"Không xác định được duy nhất bundle root: {candidates}")
    source = candidates[0]
    if list(source.rglob("test.parquet")):
        raise RuntimeError("Gói M0 không được chứa test.parquet")
    manifest = json.loads((source / "BUNDLE_MANIFEST.json").read_text(encoding="utf-8"))
    failures = []
    for item in manifest["files"]:
        path = source / item["path"]
        if not path.is_file() or path.stat().st_size != int(item["bytes"]) or sha256_file(path) != item["sha256"]:
            failures.append(item["path"])
    if failures:
        raise RuntimeError(f"Bundle có file thiếu/sai hash: {failures}")
    if SOURCE.exists():
        shutil.rmtree(SOURCE)
    try:
        os.symlink(source, SOURCE, target_is_directory=True)
    except OSError:
        shutil.copytree(source, SOURCE)
    execution["resolved_bundle_root"] = str(source)
    execution["bundle_manifest_schema"] = manifest.get("schema_version")
    execution["bundle_source_file_count"] = manifest.get("source_file_count")


def add_if_exists(archive, source, name):
    source = Path(source)
    if source.exists():
        archive.add(source, arcname=name)


def package_evidence():
    execution["finished_utc"] = datetime.now(timezone.utc).isoformat()
    STATUS.write_text(json.dumps(execution, ensure_ascii=False, indent=2), encoding="utf-8")
    if ARCHIVE.exists():
        ARCHIVE.unlink()
    with tarfile.open(ARCHIVE, "w:gz") as archive:
        add_if_exists(archive, REPO / "artifacts", "artifacts")
        add_if_exists(archive, M0_DOCS, "m0_docs/cq_v3")
        add_if_exists(archive, STATUS, STATUS.name)
        add_if_exists(archive, LOG, LOG.name)
        add_if_exists(archive, WORKING / "repository_commit_cq_v3_m0.txt", "repository_commit_cq_v3_m0.txt")
        for name in (*FULLTRAIN_CONFIGS, HEADROOM_FULLTRAIN, *HEADROOM_C02):
            add_if_exists(archive, REPO / "configs" / name, f"configs/{name}")
    print("Archive:", ARCHIVE, flush=True)


LOG.write_text("CQ V3 M0 conditional-GO packet -- train/dev only\n", encoding="utf-8")
try:
    step("00_gpu_preflight", require_t4)
    step("01_clone_and_pin", clone_and_pin)
    step("02_install", lambda: run([
        sys.executable, "-m", "pip", "install", "-q", "-e", f"{REPO}[boosting,dev]",
    ]))
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO / "src") + os.pathsep + str(REPO)
    M0_DOCS.mkdir(parents=True, exist_ok=True)
    step("03_resolve_and_verify_private_bundle", resolve_private_bundle)
    pytest_files = (
        "tests/test_course_quality_v1_adapter.py", "tests/test_cq_m0_audit.py",
        "tests/test_cq_raw_contract.py", "tests/test_cq_protocol.py",
        "tests/test_cq_patch_1013_contracts.py", "tests/test_feature_views.py",
        "tests/test_weights.py", "tests/test_headroom.py",
        "tests/test_cq_headroom_evidence.py", "tests/test_course_metrics.py",
        "tests/test_training_protocol.py", "tests/test_cq_dev_endpoints.py",
    )
    step("04_pytest_m0_contracts", lambda: run([
        sys.executable, "-m", "pytest", *pytest_files,
        "--junitxml", M0_DOCS / "pytest_m0_contracts.xml",
    ], cwd=REPO, env=env))
    prepare_config = REPO / "configs" / FULLTRAIN_CONFIGS[0]
    step("05_prepare_pool_b_joint_train_only", lambda: run([
        sys.executable, "-m", "skq_exp.cli", "prepare-external",
        "--config", prepare_config, "--input-dir", SOURCE,
        "--dataset", "course_quality_v1", "--overwrite",
    ], cwd=REPO, env=env))
    processed = REPO / "data" / "processed" / "course_quality_v1"
    probe_json = M0_DOCS / "m0_probes_dev_summary.json"
    step("06_d02_to_d06_probes", lambda: run([
        sys.executable, REPO / "scripts" / "run_cq_v1_m0_probes.py",
        "--input-dir", SOURCE, "--processed-dir", processed,
        "--output", probe_json,
    ], cwd=REPO, env=env))
    step("07_data_card_and_checks", lambda: run([
        sys.executable, REPO / "scripts" / "audit_cq_v1_m0.py",
        "--input-dir", SOURCE, "--output-dir", M0_DOCS,
        "--root-policy", "pending", "--probe-evidence", probe_json,
    ], cwd=REPO, env=env))

    for policy, name in zip(("balanced", "natural"), FULLTRAIN_CONFIGS):
        config = REPO / "configs" / name
        step(f"08_fulltrain_b_{policy}_lr_xgb", lambda config=config: run([
            sys.executable, "-m", "skq_exp.cli", "run",
            "--config", config, "--resume",
        ], cwd=REPO, env=env))
        experiment_id = name.removesuffix(".json")
        step(f"09_dev_endpoints_{policy}", lambda experiment_id=experiment_id: run([
            sys.executable, REPO / "scripts" / "compute_cq_v1_dev_endpoints.py",
            "--input-dir", SOURCE, "--artifact-root", REPO / "artifacts",
            "--experiment-id", experiment_id, "--n-min", "30",
            "--root-policy", "provisional_course_id",
        ], cwd=REPO, env=env))

    headroom_fulltrain = REPO / "configs" / HEADROOM_FULLTRAIN
    step("10_headroom_fulltrain_b_natural_xgb", lambda: run([
        sys.executable, "-m", "skq_exp.cli", "run",
        "--config", headroom_fulltrain, "--resume",
    ], cwd=REPO, env=env))
    for index, name in enumerate(HEADROOM_C02, start=1):
        config = REPO / "configs" / name
        step(f"11_headroom_c02_{index}", lambda config=config: run([
            sys.executable, "-m", "skq_exp.cli", "run",
            "--config", config, "--resume",
        ], cwd=REPO, env=env))
    headroom_output = M0_DOCS / "m0_headroom_decision_cq_v3.json"
    command = [
        sys.executable, REPO / "scripts" / "compute_cq_v1_headroom.py",
        "--artifact-root", REPO / "artifacts",
        "--fulltrain-config", headroom_fulltrain,
        "--output", headroom_output,
    ]
    for name in HEADROOM_C02:
        command.extend(["--c02-config", REPO / "configs" / name])
    step("12_compute_rho_star", lambda: run(command, cwd=REPO, env=env))
    execution["status"] = "success_conditional_go_evidence_ready"
except Exception as error:
    execution["status"] = "failed_diagnostic_archive_created"
    execution["fatal_error_type"] = type(error).__name__
    execution["fatal_error"] = str(error)
    with LOG.open("a", encoding="utf-8") as stream:
        stream.write("\nFATAL ERROR\n" + traceback.format_exc())
    print(traceback.format_exc(), flush=True)
    raise
finally:
    package_evidence()
    print("Test files were excluded; no test metric was opened.")
    print("FullTrain-A, root identity and split deviation still need written approval.")
