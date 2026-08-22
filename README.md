# Conformal Regression Shift Stress Test

Research artifact for **“Stress-Testing Conformal Regression Under Covariate Shift: A Reproducible Benchmark of Coverage, Weight Reliability, and Interval Usability.”**

Author: **Ercan Erkalkan** — Marmara University, Vocational School of Technical Sciences, Department of Electronics and Automation, Artificial Intelligence Operator Program. ORCID: `0000-0001-9259-7112`.

## Scope

This repository provides a reproducible **robustness-benchmarking and stress-testing artifact** for conformal regression under controlled and natural distribution shift. It does not introduce a new conformal construction. Instead, it evaluates complete conformal regression pipelines while keeping coverage degradation, correction mechanism, weight reliability, effective calibration information, predictor sensitivity, and interval usability separate.

## Post-freeze robustness expansions

Five explicit sensitivity/validation layers broaden the frozen core without redefining its primary comparisons.

### P0-2 — contemporary correction mechanisms

KMM-CP and randomly localized conformal prediction (RLCP) are evaluated on all five synthetic shift families in the representative nonlinear/heteroscedastic setting and on all five public directional datasets using the full frozen repetition indices. KMM-CP reduces accumulated undercoverage relative to ordinary SCP on four of five synthetic paths and four of five public datasets; RLCP gives smaller but similarly broad gains.

### P0-3 — density-ratio estimator families

The Ridge-WCP wrapper, split/seed construction, target draws, and shift paths are held fixed while the density-ratio estimator changes among locked linear-logistic odds, nonlinear histogram-gradient-boosting odds, and direct uLSIF. Results show estimator–shift-geometry interaction rather than a universally best estimator and demonstrate that high effective sample size is not equivalent to correct weighting.

### P0-4 — common-backbone factorial separation

P0-4 separates conformal-wrapper and predictor-backbone effects. The synthetic 2×2 factorial crosses `{SCP, known-ratio WCP}` with `{Ridge, mean-GBR}` over 30 paired repetitions. The public extension crosses `{SCP, known-tilt WCP}` with `{Ridge, HGBR}` over all five datasets, 20 paired repetitions, and directional/radial shifts. Known-weight WCP accumulated-undercoverage is substantially more backbone-stable than ordinary SCP in these stress constructions.

### P0-5 — high-dimensional nuisance-coordinate isolation

P0-5 closes the low-dimensional synthetic limitation with a deliberately confound-controlled sensitivity at `p={5,20,50,100}`. The Ridge predictor and conformity score always use the same first five true signal coordinates, while oracle and estimated density ratios use all `p` covariates. Four analytic shift families, severity anchors `{0,1,2}`, and 30 paired repetitions yield 4,320 frozen method-condition rows.

Estimated-WCP `p=100 - p=5` accumulated undercoverage increases significantly in all four analytic families, while the corresponding Oracle-WCP differences include zero in all four. At the true zero-shift anchor and `p=100`, held-out domain AUC is about 0.498 yet Estimated-WCP coverage is about 0.837, calibration ESS ratio about 0.00843, and analytic log-weight RMSE about 5.66. Under `p=100` variance shift at severity 2, Oracle-WCP coverage is approximately 0.99992 while almost all intervals are unbounded.

### P0-6 — natural temporal deployment shift

P0-6 adds a **non-engineered chronological deployment validation** using the UCI Gas Turbine NOx data. The source period is 2011-2013; 2014 and 2015 are evaluated as separate target years over 20 paired repetitions. No exponential target tilt is imposed. Practical correction methods use no target labels; a `Target-Cal-SCP-Reference` uses labeled target-year calibration outcomes only as a non-deployable diagnostic.

Source-calibrated SCP coverage falls from **0.8557 in 2014 to 0.6391 in 2015**. Logistic WCP and KMM-CP recover part of the 2015 loss (coverage 0.8151 and 0.8260), whereas the labeled-target reference remains near nominal coverage (0.8954 and 0.8999) and widens from 2.475 to 3.170. HGB weighting obtains high one-sided coverage only with severe concentration and unbounded-interval fractions of 0.7229 and 0.5972. The natural layer can include conditional/process drift as well as covariate drift and is therefore not treated as an exact covariate-shift validity experiment.

Compact P0-2 through P0-6 records are versioned under `analysis/`; complete frozen per-repetition tables are archived in the manuscript reproducibility supplement rather than duplicated into Git history.

## Repository map

```text
synthetic/       locked synthetic runner, tests, primary results, pre-specified sensitivities
real_data/       UCI acquisition/validation, final runner, tests, directional + radial outputs
analysis/        comparator, estimator, backbone, dimension, and temporal-shift expansions
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
| P0-4 backbone factorial — synthetic | 17,040 |
| P0-4 backbone factorial — public | 3,200 |
| P0-5 high-dimensional weighting stress | 4,320 |
| P0-6 natural temporal deployment validation | 240 |

Real-data configuration SHA-256: `b1aeef06011ba4c112737e9622f6a5adc477e87e76d36ebad5b6557871b6805a`.

## Quick verification

```bash
python -m pip install -r requirements.txt
python verify_release.py
(cd synthetic && PYTHONPATH=src python -m pytest -q tests/test_v10.py)
(cd real_data && PYTHONPATH=code python -m pytest -q tests)
```

See [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md) for the locked core workflow, [`analysis/p05_highdim`](analysis/p05_highdim) for the high-dimensional stress, and [`analysis/p06_natural_temporal`](analysis/p06_natural_temporal) for the natural chronological deployment layer. The cumulative manuscript supplement verifies P0-2 through P0-6 and ends with `P0-6 VERIFY: PASS`.

## Data policy

Raw third-party UCI files are not redistributed. The repository provides official acquisition code, frozen schema rules, UCI identifiers, canonical SHA-256 values, compact summaries, audit tables, manifests, and executable code. Complete deterministic post-freeze tables are retained in the manuscript supplement when useful for auditability.

## Scientific provenance

- Synthetic master seed: `2026081601`.
- Real-data master seed: `2026081602`.
- Nominal coverage: `0.90`.
- Persistent undercoverage alarm: mean coverage `< 0.87` for two adjacent positive severities; a CI-confirmed companion is also reported.
- Information-fragility alarm: `ESS / n_cal <= 0.20` for two adjacent positive severities.
- Usability alarm: infinite-interval fraction `>= 0.05` for two adjacent positive severities.
- Primary density-ratio estimator: standardized polynomial logistic domain classifier, `C=0.1`; sensitivity `C=0.01`.
- P0-3 alternatives: histogram-gradient-boosting classifier odds and direct uLSIF.
- P0-4 synthetic backbones: Ridge(alpha=1) and mean GBR; public backbones: Ridge(alpha=1) and HGBR.
- P0-5 predictor isolation: first five signal coordinates fixed for prediction; all `p` coordinates used for weighting.
- P0-6 chronology: 2011-2013 source; 2014/2015 separate natural target years; no engineered tilt.

Operational thresholds are reproducible stress-test landmarks, not universal theoretical constants.

## Citation

Citation metadata are provided in [`CITATION.cff`](CITATION.cff).

## Reuse

No separate software license is declared in this archival release. Third-party UCI datasets remain subject to their source terms. For reuse beyond scholarly verification/citation, contact the author.
