# Conformal Regression Shift Stress Test

Research artifact for **“Stress-Testing Conformal Regression Under Covariate Shift: A Reproducible Benchmark of Coverage, Weight Reliability, and Interval Usability.”**

Author: **Ercan Erkalkan** — Marmara University, Vocational School of Technical Sciences, Department of Electronics and Automation, Artificial Intelligence Operator Program. ORCID: `0000-0001-9259-7112`.

## Scope

This repository provides a reproducible **robustness-benchmarking and stress-testing artifact** for conformal regression under controlled covariate shift. It does not introduce a new conformal construction. Instead, it evaluates complete conformal regression pipelines over increasing shift severity while keeping distinct failure mechanisms separate.

The benchmark tracks:

1. trajectory-level coverage degradation rather than only a terminal shift point;
2. paired pathwise differences between conformal pipelines;
3. known-ratio or controlled-reference correction versus estimated-weight behavior;
4. weight concentration and effective calibration information;
5. interval usability, including unbounded weighted intervals;
6. direct estimated-versus-reference weight agreement when an auditable reference is available.

## Post-freeze robustness expansions

Two explicit sensitivity layers broaden the frozen core without redefining its primary comparisons.

### P0-2 — contemporary correction mechanisms

KMM-CP and randomly localized conformal prediction (RLCP) are evaluated on all five synthetic shift families in the representative nonlinear/heteroscedastic setting and on all five public directional datasets using the full frozen repetition indices. KMM-CP reduces accumulated undercoverage relative to ordinary SCP on four of five synthetic paths and four of five public datasets; RLCP gives smaller but similarly broad gains.

### P0-3 — density-ratio estimator families

The Ridge-WCP wrapper, split/seed construction, target draws, and shift paths are held fixed while only the density-ratio estimator changes:

- locked standardized linear logistic classifier odds;
- nonlinear histogram gradient boosting classifier odds;
- direct uLSIF least-squares density-ratio estimation.

The P0-3 layer covers all five synthetic shift families with 30 repetitions and all five UCI datasets with 20 repetitions under both directional and radial controlled shifts. The results show estimator–shift-geometry interaction rather than a universally best estimator. HGB improves construction-reference weight fidelity across the public radial shifts but does not uniformly improve one-sided undercoverage. uLSIF supplies a particularly clear warning that high effective sample size is not equivalent to correct weighting: on every synthetic shift it has lower concentration than logistic while producing larger accumulated undercoverage.

Compact P0-2 and P0-3 records are versioned under `analysis/`.

## Repository map

```text
synthetic/       locked synthetic runner, tests, primary results, pre-specified sensitivities
real_data/       UCI acquisition/validation, final runner, tests, directional + radial outputs
analysis/        post-primary robustness analyses, comparator expansions, compact outputs
docs/protocols/  final locked protocols and accepted amendments
```

## Frozen primary evidence

| layer | method-result rows | seed rows |
|---|---:|---:|
| Synthetic primary | 14,520 | 3,000 |
| Real directional | 2,500 | 500 |
| Real radial | 600 | 120 |

Additional post-freeze evidence:

| layer | frozen result rows |
|---|---:|
| P0-2 contemporary comparator — synthetic | 3,630 |
| P0-2 contemporary comparator — public | 2,500 |
| P0-3 estimator-family stress — synthetic | 2,850 |
| P0-3 estimator-family stress — public | 3,200 |

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

Raw third-party UCI files are not redistributed. The repository provides official acquisition code, frozen schema rules, UCI identifiers, and canonical SHA-256 values. Compact final summaries, breakpoint tables, merge/configuration manifests, acquisition checksums, and executable code are versioned. Large deterministic per-repetition tables may be regenerated from the locked master seeds; the manuscript supplement archives the frozen P0-2/P0-3 result tables and verification manifests.

## Scientific provenance

- Synthetic master seed: `2026081601`.
- Real-data master seed: `2026081602`.
- Nominal coverage: `0.90`.
- Persistent undercoverage alarm: mean coverage `< 0.87` for two adjacent positive severities; a CI-confirmed companion is also reported.
- Information-fragility alarm: `ESS / n_cal <= 0.20` for two adjacent positive severities.
- Usability alarm: infinite-interval fraction `>= 0.05` for two adjacent positive severities.
- Primary density-ratio estimator: standardized linear logistic domain classifier, `C=0.1`; sensitivity `C=0.01`.
- P0-3 alternatives: histogram gradient boosting classifier odds and direct uLSIF.

Operational thresholds are reproducible stress-test landmarks, not universal theoretical constants.

## Citation

Citation metadata are provided in [`CITATION.cff`](CITATION.cff).

## Reuse

No separate software license is declared in this archival release. Third-party UCI datasets remain subject to their source terms. For reuse beyond scholarly verification/citation, contact the author.
