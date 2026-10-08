"""Adapter KIP và MTT từ repo benchmark TDBench đã khóa commit.

Trạng thái: benchmark-source adapter, không tuyên bố là native source của paper
KIP/MTT hay tái lập toàn bộ thiết lập paper. Adapter gọi hàm TDBench ở commit đã
khóa, đổi budget tổng sang số mẫu mỗi lớp theo contract của repo và áp dụng các
bản vá hẹp, có khai báo trong diagnostics: import JAX hiện hành cho KIP; bật
gradient, snapshot đúng expert và lấy mẫu quỹ đạo biến thiên cho MTT theo cơ chế
code MTT chính thức. KIP sinh dữ liệu bằng kernel inducing points; MTT sinh dữ
liệu bằng cách khớp quỹ đạo huấn luyện. Loại đầu ra của cả hai là bảng train tổng
hợp, không phải subset dòng thật.

KIP/MTT được đưa vào bài làm baseline dataset distillation mạnh để so sánh utility
của một tập train rất nhỏ với SKQ. Adapter không đặt trần số dòng tùy ý: budget là
biến thực nghiệm và số dòng thực sinh luôn được lưu. Chỉ preflight RAM/phép tính
hoặc lỗi tài nguyên thật mới tạo trạng thái OOM/timeout; tuyệt đối không dùng
fallback rồi giữ nguyên tên.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
import time
import types
from pathlib import Path
from typing import Any

import numpy as np

from ..contracts import exact_budget_size
from ..native.common import verify_locked_repo
from ...resources import ResourceLimitError
from .result import GeneratedDatasetResult


class TDBenchGenerator:
    def __init__(self, method_id: str, repo_root: Path, seed: int, options: dict[str, Any] | None = None):
        self.method_id = method_id
        self.repo_root = Path(repo_root)
        self.seed = int(seed)
        self.options = dict(options or {})

    def generate(self, X_train: np.ndarray, y_train: np.ndarray, budget_ratio: float, **kwargs):
        requested = exact_budget_size(len(y_train), budget_ratio)
        repo = self.repo_root / "tdbench"
        if not (repo / "tabdd" / "distill").exists():
            return GeneratedDatasetResult.failure(
                self.method_id, "blocked", requested, f"Thiếu repo TDBench: {repo}"
            )
        try:
            commit = verify_locked_repo(repo)
        except RuntimeError as error:
            return GeneratedDatasetResult.failure(
                self.method_id, "blocked", requested, str(error)
            )
        labels = np.unique(y_train)
        per_label, budget_diagnostics = _plan_tdbench_budget(
            self.method_id, np.asarray(y_train), requested
        )
        if per_label < 1:
            result = GeneratedDatasetResult.failure(
                self.method_id, "budget_infeasible", requested,
                budget_diagnostics["budget_limitation_reason"],
            )
            result.diagnostics.update(budget_diagnostics)
            return result
        started = time.perf_counter()
        resource_guard = kwargs.get("resource_guard")
        try:
            if resource_guard is not None:
                resource_guard.check("trước khi gọi TDBench")
            if self.method_id == "s_kip_tdbench":
                module = _load_distill_module(repo, "kip")
                X_syn, y_syn = module.kip(
                    np.asarray(X_train), np.asarray(y_train), per_label,
                    n_epochs=int(self.options.get("n_epochs", 100)),
                    mlp_dim=int(self.options.get("mlp_dim", 128)),
                    random_state=self.seed,
                )
            elif self.method_id == "s_mtt_tdbench":
                module = _load_distill_module(repo, "trajectory_matching")
                X_syn, y_syn = module.trajectory_matching(
                    np.asarray(X_train), np.asarray(y_train), per_label,
                    n_epochs=int(self.options.get("n_epochs", 20)),
                    n_experts=int(self.options.get("n_experts", 2)),
                    expert_epochs=int(self.options.get("expert_epochs", 2)),
                    syn_steps=int(self.options.get("syn_steps", 5)),
                    max_start_epoch=int(self.options.get("max_start_epoch", 10)),
                    mlp_dim=int(self.options.get("mlp_dim", 64)),
                    n_iter=int(self.options.get("n_iter", 100)),
                    lr_teacher=float(self.options.get("lr_teacher", 0.01)),
                    lr_data=float(self.options.get("lr_data", 0.1)),
                    lr_lr=float(self.options.get("lr_lr", 1e-5)),
                    mom_lr=float(self.options.get("mom_lr", 0.5)),
                    mom_data=float(self.options.get("mom_data", 0.5)),
                    n_hidden_layers=int(self.options.get("n_hidden_layers", 2)),
                    random_state=self.seed,
                )
            else:
                raise KeyError(self.method_id)
            if resource_guard is not None:
                resource_guard.check("sau khi gọi TDBench")
        except (ModuleNotFoundError, ImportError) as error:
            return GeneratedDatasetResult.failure(
                self.method_id, "blocked", requested,
                f"Dependency TDBench chưa đủ: {error}",
            )
        except ResourceLimitError as error:
            return _resource_failure(
                self.method_id, error.status, requested, str(error), budget_diagnostics
            )
        except MemoryError as error:
            return _resource_failure(
                self.method_id, "oom", requested,
                f"Runtime hết RAM khi chạy TDBench: {error!r}", budget_diagnostics,
            )
        except Exception as error:
            resource_status = _classify_resource_exception(error)
            if resource_status is not None:
                return _resource_failure(
                    self.method_id, resource_status, requested,
                    f"TDBench dừng vì tài nguyên: {error!r}", budget_diagnostics,
                )
            return GeneratedDatasetResult.failure(
                self.method_id, "failed", requested,
                f"TDBench trả lỗi, không dùng fallback: {error!r}",
            )
        X_syn = np.asarray(X_syn, dtype=np.float32)
        y_syn = np.asarray(y_syn, dtype=np.int64)
        if (
            X_syn.ndim != 2 or y_syn.ndim != 1 or len(X_syn) != len(y_syn)
            or X_syn.shape[1] != X_train.shape[1] or len(X_syn) == 0
            or not np.isfinite(X_syn).all()
            or not set(np.unique(y_syn).tolist()) <= set(labels.tolist())
            or set(np.unique(y_syn).tolist()) != set(labels.tolist())
        ):
            return GeneratedDatasetResult.failure(
                self.method_id, "failed", requested,
                "TDBench output vi phạm shape/finite/label coverage contract",
            )
        if self.method_id == "s_mtt_tdbench":
            exact_pairs = _count_exact_training_pairs(X_syn, y_syn, X_train, y_train)
            if exact_pairs == len(X_syn):
                return GeneratedDatasetResult.failure(
                    self.method_id,
                    "failed",
                    requested,
                    "MTT không cập nhật dữ liệu tổng hợp: toàn bộ output vẫn là dòng train gốc",
                )
        else:
            exact_pairs = None
        elapsed = time.perf_counter() - started
        source_patches = list(getattr(module, "__skq_source_patches__", ()))
        return GeneratedDatasetResult(
            X=X_syn,
            y=y_syn,
            weights=np.ones(len(y_syn), dtype=np.float64),
            requested_rows=requested,
            realized_rows=len(y_syn),
            generator_id=self.method_id,
            diagnostics={
                "upstream_repo": "https://github.com/inwonakng/tdbench.git",
                "upstream_commit": commit,
                "execution_mode": (
                    "pinned_upstream_source_with_declared_patch"
                    if source_patches else "pinned_upstream_source_function"
                ),
                "fidelity": (
                    "benchmark-source adapter; bản vá tương thích/khôi phục gradient "
                    "được khai báo, không phải chạy nguyên trạng TDBench"
                ),
                "source_patches": source_patches,
                "budget_contract": budget_diagnostics["budget_contract"],
                "n_per_label": int(per_label),
                **budget_diagnostics,
                "class_counts": {str(int(v)): int(np.sum(y_syn == v)) for v in np.unique(y_syn)},
                "exact_training_pairs": exact_pairs,
                "storage_bytes_float32": int(X_syn.astype(np.float32).nbytes + y_syn.nbytes),
            },
            timings={"generate": elapsed, "total": elapsed},
        )


def _plan_tdbench_budget(
    method_id: str, y_train: np.ndarray, requested: int,
) -> tuple[int, dict[str, Any]]:
    """Đổi budget tổng sang budget mỗi lớp mà source TDBench thật sự chạy được.

    KIP của TDBench lấy ``10 * N`` dòng thật ở *mỗi lớp*, không hoàn lại. Vì vậy
    N không thể lớn hơn ``min_class_count // 10``. Đây là ràng buộc đầu vào của
    source, không phải resource gate và không được báo nhầm thành timeout/OOM.
    """
    labels, counts = np.unique(y_train, return_counts=True)
    n_classes = int(len(labels))
    requested_per_label = requested // n_classes if n_classes else 0
    per_label = requested_per_label
    diagnostics: dict[str, Any] = {
        "requested_total_rows": int(requested),
        "requested_per_label": int(requested_per_label),
        "number_of_classes": n_classes,
        "minimum_class_rows": int(counts.min()) if len(counts) else 0,
        "source_feasibility_limited": False,
        "budget_contract": "TDBench n/L; realized = floor(requested/classes)*classes",
    }
    if method_id == "s_kip_tdbench" and len(counts):
        target_multiplier = 10
        source_limit = int(counts.min() // target_multiplier)
        per_label = min(requested_per_label, source_limit)
        diagnostics.update({
            "kip_target_multiplier": target_multiplier,
            "source_max_per_label": source_limit,
            "source_feasibility_limited": per_label < requested_per_label,
            "budget_contract": (
                "KIP-TDBench N/lớp; source lấy 10*N dòng thật/lớp không hoàn lại; "
                "realized = min(floor(requested/classes), floor(min_class/10))*classes"
            ),
        })
    diagnostics["planned_per_label"] = int(per_label)
    diagnostics["planned_realized_rows"] = int(per_label * n_classes)
    if per_label < 1:
        if n_classes == 0:
            reason = "Tập train không có nhãn nên TDBench không thể sinh dữ liệu"
        elif method_id == "s_kip_tdbench" and requested_per_label >= 1:
            reason = (
                "KIP-TDBench cần ít nhất 10 dòng thật ở mỗi lớp vì source lấy "
                "target batch 10*N không hoàn lại"
            )
        else:
            reason = "Budget tổng nhỏ hơn số lớp theo contract n/L của TDBench"
        diagnostics["budget_limitation_reason"] = reason
    else:
        diagnostics["budget_limitation_reason"] = ""
    return int(per_label), diagnostics


def _classify_resource_exception(error: Exception) -> str | None:
    """Nhận diện lỗi tài nguyên phổ biến của CUDA/JAX mà không import framework."""
    text = f"{type(error).__name__}: {error}".lower()
    oom_markers = (
        "out of memory", "resource exhausted", "resource_exhausted",
        "cudaerroroutofmemory", "cuda out of memory", "cannot allocate memory",
    )
    if any(marker in text for marker in oom_markers):
        return "oom"
    if "timed out" in text or "timeout" in text:
        return "timeout"
    return None


def _resource_failure(
    method_id: str,
    status: str,
    requested: int,
    reason: str,
    budget_diagnostics: dict[str, Any],
) -> GeneratedDatasetResult:
    result = GeneratedDatasetResult.failure(method_id, status, requested, reason)
    result.diagnostics.update({
        **budget_diagnostics,
        "resource_failure": True,
        "resource_status": status,
    })
    return result


def _load_distill_module(repo: Path, module_name: str):
    """Nạp file upstream với các bản vá hẹp, kiểm chứng được và có provenance."""
    root = repo / "tabdd" / "distill"
    package_name = "_skq_tdbench_distill"
    package = sys.modules.get(package_name)
    if package is None:
        package = types.ModuleType(package_name)
        package.__path__ = [str(root)]
        sys.modules[package_name] = package
    for dependency in ("random_sample", "utils"):
        qualified = f"{package_name}.{dependency}"
        if qualified not in sys.modules:
            spec = importlib.util.spec_from_file_location(qualified, root / f"{dependency}.py")
            loaded = importlib.util.module_from_spec(spec)
            sys.modules[qualified] = loaded
            assert spec.loader is not None
            spec.loader.exec_module(loaded)
    qualified = f"{package_name}.{module_name}"
    source_path = root / f"{module_name}.py"
    source = source_path.read_text(encoding="utf-8")
    source, source_patches = _patch_tdbench_source(module_name, source)
    spec = importlib.util.spec_from_file_location(qualified, source_path)
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[qualified] = loaded
    exec(compile(source, str(source_path), "exec"), loaded.__dict__)
    loaded.__skq_source_patches__ = tuple(source_patches)
    return loaded


def _patch_tdbench_source(module_name: str, source: str) -> tuple[str, list[str]]:
    """Áp dụng patch tối thiểu; source lệch mẫu đã khóa thì dừng thay vì vá mơ hồ."""
    patches: list[str] = []
    if module_name == "kip":
        source = _replace_once(
            source,
            "import jax.config\nfrom jax.config import config as jax_config",
            "from jax import config as jax_config",
            "kip_jax_config_import_compat",
        )
        patches.append("kip_jax_config_import_compat")
    elif module_name == "trajectory_matching":
        source = _replace_once(
            source,
            "random_state = expert_seeds[0]",
            "random_state = expert_seeds[i]",
            "mtt_distinct_expert_seeds",
        )
        source = _replace_once(
            source,
            "trajectories.append([p.detach().cpu() for p in model.parameters()])\n"
            "        opt_model = optim.SGD",
            "trajectories.append([p.detach().cpu().clone() for p in model.parameters()])\n"
            "        opt_model = optim.SGD",
            "mtt_clone_initial_expert_snapshot",
        )
        source = _replace_once(
            source,
            "trajectories.append([p.detach().cpu() for p in model.parameters()])\n"
            "        all_trajectories.append",
            "trajectories.append([p.detach().cpu().clone() for p in model.parameters()])\n"
            "        all_trajectories.append",
            "mtt_clone_epoch_expert_snapshots",
        )
        source = _replace_once(
            source,
            "X_syn = torch.tensor(X[support_idxs]).float().to(device)",
            "X_syn = torch.tensor(X[support_idxs]).float().to(device).requires_grad_(True)",
            "mtt_trainable_synthetic_data",
        )
        source = _replace_once(
            source,
            "syn_lr = torch.tensor(lr_teacher).to(device)",
            "syn_lr = torch.tensor(lr_teacher).to(device).requires_grad_(True)",
            "mtt_trainable_learning_rate",
        )
        source = _replace_once(
            source,
            "param_cache = {}\n\n"
            "    for it in range(n_iter):",
            "param_cache = {}\n"
            "    rng = random.Random(random_state)\n\n"
            "    for it in range(n_iter):",
            "mtt_persistent_trajectory_rng",
        )
        source = _replace_once(
            source,
            "        rng = random.Random(random_state)\n"
            "        start_epoch = rng.randint(0, max_start_epoch)",
            "        start_epoch = rng.randint(0, max_start_epoch)",
            "mtt_remove_per_iteration_rng_reset",
        )
        patches.extend([
            "mtt_distinct_expert_seeds",
            "mtt_clone_initial_expert_snapshot",
            "mtt_clone_epoch_expert_snapshots",
            "mtt_trainable_synthetic_data",
            "mtt_trainable_learning_rate",
            "mtt_persistent_trajectory_rng",
            "mtt_remove_per_iteration_rng_reset",
        ])
    return source, patches


def _replace_once(source: str, old: str, new: str, patch_id: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(
            f"Không thể áp dụng patch {patch_id}: cần đúng 1 vị trí, tìm thấy {count}"
        )
    return source.replace(old, new, 1)


def _count_exact_training_pairs(
    X_generated: np.ndarray,
    y_generated: np.ndarray,
    X_train: np.ndarray,
    y_train: np.ndarray,
) -> int:
    """Đếm output trùng hoàn toàn cặp (features, label) của tập train."""
    generated = np.asarray(X_generated, dtype=np.float32)
    reference = np.asarray(X_train, dtype=np.float32)
    reference_pairs = {
        (np.ascontiguousarray(row).tobytes(), int(label))
        for row, label in zip(reference, np.asarray(y_train).reshape(-1), strict=True)
    }
    return sum(
        (np.ascontiguousarray(row).tobytes(), int(label)) in reference_pairs
        for row, label in zip(generated, np.asarray(y_generated).reshape(-1), strict=True)
    )
