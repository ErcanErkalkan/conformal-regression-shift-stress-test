# Conformal Regression Shift Stress Test

Research artifact for **“Stress-Testing Conformal Regression Under Controlled Covariate Shift: Validity Breakpoints, Weight Fragility, and Interval Usability.”**

Author: **Ercan Erkalkan** — Marmara University, Vocational School of Technical Sciences, Department of Electronics and Automation, Artificial Intelligence Operator Program. ORCID: `0000-0001-9259-7112`.

## Scope

This repository is a reproducible **evaluation and stress-testing artifact**, not a new conformal-prediction algorithm or coverage theorem. The study separates:

1. persistent coverage/validity failure;
2. weight concentration and information fragility;
3. interval usability failure;
4. direct estimated-vs-known-tilt weight fidelity where a construction oracle is available;
5. secondary metric-specific ordering sensitivity.

The repository contains only the final scientific state. Pilot, smoke, obsolete v0.x runners, estimator-screen scratch outputs, virtual environments, caches, reviewer simulations, submission correspondence, and superseded manuscript versions are intentionally excluded. Large synthetic per-repetition tables and supplementary sensitivity raw tables are also omitted from Git history because the locked runners regenerate them deterministically; compact publication summaries, breakpoint tables, provenance manifests, checksums, and all executable code are versioned. Deterministic seed/per-repetition tables are regenerated from the locked master seeds rather than duplicated in Git history.

## Repository map

```text
synthetic/       locked synthetic runner, tests, primary results, pre-specified sensitivities
real_data/       UCI acquisition/validation, final runner, tests, directional + radial outputs
analysis/        post-primary robustness-analysis code and compact derived summaries
docs/protocols/  final locked protocols and accepted amendments
```

## Frozen primary evidence

| layer | method-result rows | seed rows |
|---|---:|---:|
| Synthetic primary | 14,520 | 3,000 |
| Real directional | 2,500 | 500 |
| Real radial | 600 | 120 |

Real-data configuration SHA-256: `b1aeef06011ba4c112737e9622f6a5adc477e87e76d36ebad5b6557871b6805a`.

## Quick verification

```bash
python -m pip install -r requirements.txt
python verify_release.py
(cd synthetic && PYTHONPATH=src python -m pytest -q tests/test_v10.py)
(cd real_data && PYTHONPATH=code python -m pytest -q tests)
```

See [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md) for complete rerun instructions and [`docs/DATASETS.md`](docs/DATASETS.md) for official UCI acquisition/checksum provenance.

## Data policy

Raw third-party UCI files are not redistributed. The repository provides official acquisition code, frozen schema rules, UCI identifiers, and canonical SHA-256 values. Compact final summaries, breakpoint tables, merge/configuration manifests, acquisition checksums, and all locked code/configuration are versioned. Seed manifests, per-repetition raw outputs, paired differences, trajectories, and supplementary sensitivity result tables are deterministic runner outputs and are intentionally regenerated rather than duplicated in Git history.

## Scientific provenance

- Synthetic master seed: `2026081601`.
- Real-data master seed: `2026081602`.
- Nominal coverage: `0.90`.
- Persistent undercoverage alarm: mean coverage `< 0.87` for two adjacent positive severities; a CI-confirmed companion is also reported.
- Information-fragility alarm: `ESS / n_cal <= 0.20` for two adjacent positive severities.
- Usability alarm: infinite-interval fraction `>= 0.05` for two adjacent positive severities.
- Primary density-ratio estimator: standardized linear logistic domain classifier, `C=0.1`; sensitivity `C=0.01`.

Operational thresholds are reproducible stress-test landmarks, not universal theoretical constants.

## Citation

Citation metadata are provided in [`CITATION.cff`](CITATION.cff).

## Reuse

No separate software license is declared in this archival release. Third-party UCI datasets remain subject to their source terms. For reuse beyond scholarly verification/citation, contact the author.
