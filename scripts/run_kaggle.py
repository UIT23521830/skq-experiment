"""Script này là entry point ngắn cho Kaggle Notebook.

Nó nhận một config và gọi runner trong package; mọi thuật toán vẫn nằm trong
`src/skq_exp`. Nhờ vậy notebook chỉ điều phối, không chứa một bản code khác khó
đối chiếu với GitHub.
"""

from __future__ import annotations

import argparse
import json

from skq_exp.config import ExperimentConfig
from skq_exp.experiments import run_config


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--dataset")
    args = parser.parse_args()
    config = ExperimentConfig.from_json(args.config)
    print(json.dumps(run_config(config, dataset_id=args.dataset), indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

