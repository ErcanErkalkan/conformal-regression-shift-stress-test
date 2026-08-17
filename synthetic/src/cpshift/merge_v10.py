from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import yaml

from .runner_v10 import VERSION, summarize, _sha256, config_hash, expected_raw_rows, expected_seed_rows


def merge(config_path: Path, output_dir: Path, input_dirs: list[Path]) -> None:
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    cfg_hash = config_hash(cfg)
    raws = []
    seeds = []
    shard_info = []
    for d in input_dirs:
        raw_path = d / "raw_results_v10.csv"
        seed_path = d / "seed_manifest_v10.csv"
        man_path = d / "run_manifest_v10.json"
        if not raw_path.exists() or not seed_path.exists() or not man_path.exists():
            raise FileNotFoundError(f"incomplete shard: {d}")
        man = json.loads(man_path.read_text(encoding="utf-8"))
        if man.get("version") != VERSION:
            raise ValueError(f"version mismatch in {d}")
        if man.get("config_sha256") != cfg_hash:
            raise ValueError(f"config mismatch in {d}; refusing to merge shards from different designs")
        raws.append(pd.read_csv(raw_path))
        seeds.append(pd.read_csv(seed_path))
        shard_info.append({"dir": str(d), "rep_start": man["rep_start"], "rep_end": man["rep_end"]})

    raw = pd.concat(raws, ignore_index=True)
    key = ["rep", "dgp", "noise", "shift_family", "severity", "method"]
    if raw.duplicated(key).any():
        dup = raw[raw.duplicated(key, keep=False)][key].head(10).to_dict("records")
        raise RuntimeError(f"duplicate keys across shards: {dup}")
    expected_reps = set(range(int(cfg["repetitions"])))
    got_reps = set(int(x) for x in raw["rep"].unique())
    if got_reps != expected_reps:
        raise RuntimeError(f"rep coverage mismatch; missing={sorted(expected_reps-got_reps)}, extra={sorted(got_reps-expected_reps)}")
    expected_rows = expected_raw_rows(cfg, int(cfg["repetitions"]))
    if len(raw) != expected_rows:
        raise RuntimeError(f"merged raw row count mismatch: got {len(raw)}, expected {expected_rows}")

    seed_all = pd.concat(seeds, ignore_index=True).drop_duplicates()
    expected_seeds = expected_seed_rows(cfg, int(cfg["repetitions"]))
    if len(seed_all) != expected_seeds:
        raise RuntimeError(f"merged seed row count mismatch: got {len(seed_all)}, expected {expected_seeds}")

    output_dir.mkdir(parents=True, exist_ok=True)
    raw = raw.sort_values(key).reset_index(drop=True)
    raw.to_csv(output_dir / "raw_results_v10.csv", index=False)
    seed_all.sort_values(["rep", "dgp", "noise", "shift_family", "severity"]).to_csv(output_dir / "seed_manifest_v10.csv", index=False)
    summarize(raw, cfg, output_dir)
    (output_dir / "merge_manifest_v10.json").write_text(json.dumps({"version": VERSION, "config_sha256": cfg_hash, "expected_raw_rows": expected_rows, "expected_seed_rows": expected_seeds, "shards": shard_info}, indent=2), encoding="utf-8")
    checksums = []
    for pth in sorted(output_dir.iterdir()):
        if pth.is_file() and pth.name != "checksums_v10.json":
            checksums.append({"file": pth.name, "sha256": _sha256(pth), "bytes": pth.stat().st_size})
    (output_dir / "checksums_v10.json").write_text(json.dumps(checksums, indent=2), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("input_dirs", nargs="+")
    a = ap.parse_args()
    merge(Path(a.config), Path(a.output_dir), [Path(x) for x in a.input_dirs])


if __name__ == "__main__":
    main()
