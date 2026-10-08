"""Package này gom artifact đã có thành bảng dài và bảng so sánh.

Nó không chạy lại selector hay model. Nhờ vậy việc chỉnh cách trình bày không làm
thay đổi prediction và mỗi số trong báo cáo vẫn truy ngược được về run_id.
"""

from .aggregate import aggregate_results

__all__ = ["aggregate_results"]

