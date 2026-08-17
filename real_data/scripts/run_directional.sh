#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT/code"
python code/download_uci_data.py --manifest configs/dataset_manifest.json --out data/canonical
python code/validate_data.py --manifest configs/dataset_manifest.json --data-dir data/canonical
python -m pytest -q tests
mkdir -p runs/directional_shards
DATASETS=(ccpp appliances superconductivity gas_turbine_nox online_news)
for i in "${!DATASETS[@]}"; do
  d="${DATASETS[$i]}"
  for start in 0 5 10 15; do
    end=$((start+5))
    python code/run_real_benchmark.py       --config configs/real_data_prelock.json       --dataset "$d" --dataset-index "$i"       --rep-start "$start" --rep-end "$end"       --data-dir data/canonical --out runs/directional_shards
  done
done
python code/run_real_benchmark.py --config configs/real_data_prelock.json   --merge --run-dir runs/directional_shards --out runs/final_directional_v03
python code/verify_results.py --directional runs/final_directional_v03
