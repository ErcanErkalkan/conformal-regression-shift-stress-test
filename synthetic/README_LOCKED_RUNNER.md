# Conformal Regression Shift Stress Test — Protocol v1.0.1 LOCKED

This package implements the locked primary synthetic experiment for the manuscript project targeting **Communications Faculty of Sciences University of Ankara Series A1: Mathematics and Statistics**.

## Scientific boundary

This is an evaluation/stress-testing framework, not a new conformal algorithm. The locked design separates:

1. **coverage failure** — persistent one-sided undercoverage;
2. **information/support fragility** — ESS, weight concentration, MMD and direct oracle-vs-estimated weight fidelity;
3. **usability failure** — especially infinite prediction intervals under weighted conformal calibration.

Method order is evaluated metric-by-metric; no new composite super-score is introduced.

## Locked primary design

- DGPs: `linear`, `nonlinear`
- Noise: `gaussian`, `heteroscedastic`
- Shift families: `mean`, `variance`, `mixture`, `tail_mixture`, `nonlinear`
- Native severities: `0, 0.5, 1.0, 1.5, 2.0`
- Repetitions: 30 paired repetitions
- Sample sizes: train 1000, calibration 1000, test 2500, unlabeled target 1000
- Nominal coverage: 0.90
- Coverage lower acceptable bound: 0.87
- Persistent breakpoint: two consecutive severity levels
- Information fragility threshold: ESS/n_cal <= 0.20 (operational; sensitivity required)
- Infinite-interval usability threshold: >= 0.05 (operational; sensitivity required)
- Primary density-ratio estimator: degree-2 polynomial logistic, C=0.1
- Mandatory estimator sensitivity: degree-2 polynomial logistic, C=0.01

`configs/main_v10_locked.yaml` is the canonical locked configuration.

## Why sharding exists

The core has 3000 paired condition-repetitions before method rows. To keep runs auditable and manageable on a local workstation, repetitions can be split into shards without changing any random seeds. All target/source/model seeds are derived from the locked master seed and explicit condition coordinates.

### Example: six 5-repetition shards

```bash
PYTHONPATH=src python -m cpshift.runner_v10 --config configs/main_v10_locked.yaml --output-dir runs/shard_00_05 --rep-start 0  --rep-end 5
PYTHONPATH=src python -m cpshift.runner_v10 --config configs/main_v10_locked.yaml --output-dir runs/shard_05_10 --rep-start 5  --rep-end 10
PYTHONPATH=src python -m cpshift.runner_v10 --config configs/main_v10_locked.yaml --output-dir runs/shard_10_15 --rep-start 10 --rep-end 15
PYTHONPATH=src python -m cpshift.runner_v10 --config configs/main_v10_locked.yaml --output-dir runs/shard_15_20 --rep-start 15 --rep-end 20
PYTHONPATH=src python -m cpshift.runner_v10 --config configs/main_v10_locked.yaml --output-dir runs/shard_20_25 --rep-start 20 --rep-end 25
PYTHONPATH=src python -m cpshift.runner_v10 --config configs/main_v10_locked.yaml --output-dir runs/shard_25_30 --rep-start 25 --rep-end 30
```

Merge only after all six shards finish:

```bash
PYTHONPATH=src python -m cpshift.merge_v10 \
  --config configs/main_v10_locked.yaml \
  --output-dir runs/final_merged \
  runs/shard_00_05 runs/shard_05_10 runs/shard_10_15 \
  runs/shard_15_20 runs/shard_20_25 runs/shard_25_30
```

The merger rejects duplicate or missing repetition IDs.

## Smoke validation

```bash
PYTHONPATH=src python -m cpshift.runner_v10 \
  --config configs/smoke_v10.yaml \
  --output-dir runs/smoke_v10
```

## Tests

```bash
python -m pytest -q
```

## Core outputs

Every shard writes raw results, summary tables, paired comparisons, trajectory metrics, breakpoints, metric-specific rank reversals, a seed manifest, environment/code manifest and SHA-256 checksums.

### Breakpoint semantics

`B_cov` is based on **one-sided undercoverage**, not absolute coverage gap. Overcoverage is not called coverage failure.

`B_cov_CI` requires the **upper** 95% confidence bound of mean coverage to fall below 0.87 persistently. This is the conservative inferential companion to the mean-based breakpoint.

## Anti-tuning rule

Do not change locked primary thresholds, methods, severity grid, sample sizes, estimator hyperparameters or hypotheses after inspecting the v1.0 final results unless a documented implementation or mathematical error invalidates the analysis. Any such correction requires a numbered protocol amendment.


## v1.0.1 baseline/breakpoint clarification

Breakpoints are searched only over positive severities (`delta > 0`). A failure at `delta = 0` is recorded separately in `baseline_quality_flags_v10.csv`; it is never mislabeled as a shift-induced breakpoint. Threshold values and the locked experimental design are unchanged.
