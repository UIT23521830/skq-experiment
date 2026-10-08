"""File này biến dữ liệu thành đặc trưng Fourier ngẫu nhiên để xấp xỉ RBF kernel.

Bandwidth được ước lượng chỉ từ train. Phép biến đổi dùng số chiều cố định nên có
thể chạy theo batch trên dữ liệu lớn thay vì tạo ma trận kernel N×N.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def median_bandwidth(X: np.ndarray, seed: int, max_points: int = 2048) -> float:
    if len(X) < 2:
        return 1.0
    rng = np.random.default_rng(seed)
    take = min(len(X), max_points)
    sample = X[rng.choice(len(X), size=take, replace=False)].astype(np.float64, copy=False)
    # Lấy các cặp ngẫu nhiên để tránh ma trận khoảng cách bậc hai.
    pairs = min(200_000, take * 32)
    left = rng.integers(0, take, size=pairs)
    right = rng.integers(0, take, size=pairs)
    distance = np.linalg.norm(sample[left] - sample[right], axis=1)
    positive = distance[distance > 0]
    return float(np.median(positive)) if positive.size else 1.0


@dataclass
class RBFRandomFeatures:
    n_components: int = 256
    bandwidth_multiplier: float = 1.0
    seed: int = 11
    dtype: str = "float32"

    def fit(self, X: np.ndarray) -> "RBFRandomFeatures":
        sigma = median_bandwidth(X, self.seed) * self.bandwidth_multiplier
        if not np.isfinite(sigma) or sigma <= 0:
            raise ValueError("Bandwidth phải hữu hạn và dương")
        self.sigma_ = float(sigma)
        rng = np.random.default_rng(self.seed)
        self.omega_ = rng.normal(
            0.0, 1.0 / self.sigma_, size=(X.shape[1], self.n_components)
        ).astype(self.dtype)
        self.phase_ = rng.uniform(0, 2 * np.pi, size=self.n_components).astype(self.dtype)
        return self

    def transform(self, X: np.ndarray, batch_size: int = 65_536, check=None) -> np.ndarray:
        if not hasattr(self, "omega_"):
            raise RuntimeError("Phải gọi fit trước transform")
        output = np.empty((len(X), self.n_components), dtype=self.dtype)
        scale = np.sqrt(2.0 / self.n_components)
        for start in range(0, len(X), batch_size):
            if check is not None:
                check("rff")
            stop = min(start + batch_size, len(X))
            projection = np.asarray(X[start:stop], dtype=self.dtype) @ self.omega_ + self.phase_
            output[start:stop] = scale * np.cos(projection)
        return output

    def fit_transform(self, X: np.ndarray, batch_size: int = 65_536, check=None) -> np.ndarray:
        return self.fit(X).transform(X, batch_size=batch_size, check=check)

