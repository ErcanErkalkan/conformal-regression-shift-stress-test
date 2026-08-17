#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python -m pytest -q
python - <<'PY'
from pathlib import Path
import json, yaml
from cpshift.runner_v10 import config_hash, expected_raw_rows, expected_seed_rows
cfg=yaml.safe_load(Path('configs/main_v10_locked.yaml').read_text())
print('config_sha256=', config_hash(cfg))
print('expected_raw_rows=', expected_raw_rows(cfg, cfg['repetitions']))
print('expected_seed_rows=', expected_seed_rows(cfg, cfg['repetitions']))
PY
