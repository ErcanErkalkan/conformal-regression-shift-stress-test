#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH=src
CFG=configs/main_v10_locked.yaml
mkdir -p runs
for START in 0 5 10 15 20 25; do
  END=$((START+5))
  NAME=$(printf 'runs/shard_%02d_%02d' "$START" "$END")
  echo "=== Running $NAME ==="
  python -m cpshift.runner_v10 --config "$CFG" --output-dir "$NAME" --rep-start "$START" --rep-end "$END"
done
python -m cpshift.merge_v10 --config "$CFG" --output-dir runs/final_merged \
  runs/shard_00_05 runs/shard_05_10 runs/shard_10_15 runs/shard_15_20 runs/shard_20_25 runs/shard_25_30
echo "Final merged results: runs/final_merged"
