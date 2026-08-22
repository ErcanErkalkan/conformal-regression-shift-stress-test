# Conformal Regression Shift Stress Test

Research artifact for **“Stress-Testing Conformal Regression Under Covariate Shift: A Reproducible Benchmark of Coverage, Weight Reliability, and Interval Usability.”**

Author: **Ercan Erkalkan** — Marmara University, Vocational School of Technical Sciences, Department of Electronics and Automation, Artificial Intelligence Operator Program. ORCID: `0000-0001-9259-7112`.

## Scope

This repository provides a reproducible robustness-benchmarking and stress-testing artifact for conformal regression under controlled and natural distribution shift. It does not introduce a new conformal construction. It evaluates complete pipelines while keeping coverage degradation, correction mechanism, density-ratio reliability, effective calibration information, predictor sensitivity, interval usability, natural deployment drift, and computational cost separate.

## Important P1-3 terminology clarification

The evaluated kernel-mean-matching comparator is **KMM-WCP**: non-selective classical RBF kernel mean matching followed by a weighted split-conformal absolute-residual cutoff. Some immutable historical P0-2/P0-6/P0-7 result files use the string `KMM-CP-Ridge`; those frozen strings map to `KMM-WCP-Ridge` and are retained for checksum continuity. They must not be confused with the distinct published **selective KMM-CP** method of Laghuvarapu, Deb, and Sun (UAI 2026). See [`analysis/p02_comparator_expansion/METHOD_LABEL_CLARIFICATION_P1_3.md`](analysis/p02_comparator_expansion/METHOD_LABEL_CLARIFICATION_P1_3.md).

## Robustness expansions

### P0-2 — contemporary correction mechanisms

KMM-WCP and randomly localized conformal prediction (RLCP) are evaluated on all five synthetic shift families in the representative nonlinear/heteroscedastic setting and on all five public directional datasets. KMM-WCP reduces accumulated undercoverage relative to ordinary SCP on four of five synthetic paths and four of five public datasets; RLCP gives smaller but similarly broad gains.

### P0-3 — density-ratio estimator families

The Ridge-WCP wrapper, split/seed construction, target draws, and shift paths are held fixed while the density-ratio estimator changes among polynomial-logistic odds, nonlinear histogram-gradient-boosting odds, and direct uLSIF. Results show estimator–shift-geometry interaction rather than a universally best estimator and demonstrate that high effective sample size is not equivalent to correct weighting.

### P0-4 — common-backbone factorial separation

P0-4 separates conformal-wrapper and predictor-backbone effects. The synthetic 2×2 factorial crosses `{SCP, known-ratio WCP}` with `{Ridge, mean-GBR}` over 30 paired repetitions. The public extension crosses `{SCP, known-tilt WCP}` with `{Ridge, HGBR}` over all five datasets, 20 paired repetitions, and directional/radial shifts. Known-weight WCP accumulated-undercoverage is substantially more backbone-stable than ordinary SCP in these constructions.

### P0-5 — high-dimensional nuisance-coordinate isolation

P0-5 tests `p={5,20,50,100}` while the Ridge predictor and conformity score always use the same first five true signal coordinates and weighting uses all `p` covariates. Estimated-WCP `p=100 - p=5` accumulated-undercoverage intervals exclude zero above zero in all four analytic shift families, while the corresponding Oracle-WCP intervals include zero in all four. At the true zero-shift anchor and `p=100`, held-out domain AUC is about 0.498 yet Estimated-WCP coverage is about 0.837, calibration ESS ratio about 0.00843, and analytic log-weight RMSE about 5.66.

### P0-6 — natural temporal deployment shift

P0-6 adds a non-engineered chronological deployment validation using the UCI Gas Turbine NOx data. The source period is 2011-2013; 2014 and 2015 are separate target years over 20 paired repetitions, with no exponential target tilt. Source-calibrated SCP coverage falls from 0.8557 in 2014 to 0.6391 in 2015. Logistic WCP and KMM-WCP recover part of the 2015 loss, while a labeled-target calibration reference remains near nominal. The natural layer may contain conditional/process drift as well as covariate drift and is not treated as an exact covariate-shift validity experiment.

### P0-7 — computational and scalability audit

P0-7 measures eight conformal pipelines under a sequential, verified single-thread protocol. Predictor fitting, conformal calibration, ratio/localization fitting, weight evaluation, interval inference, and fresh-process peak RSS are reported separately.

At the common reference workload (`p=20`, `n_train=n_cal=n_unlabeled=n_test=1000`), median end-to-end time is about 1.72 ms for SCP-Ridge, 2.10 ms for Oracle-WCP-Ridge, 32.2 ms for uLSIF-WCP, 53.6 ms for Estimated-WCP-Logistic, 115.7 ms for RLCP, 181.3 ms for HGB-WCP, 255.9 ms for KMM-WCP, and 1.30 s for CQR-GBR. Estimated-WCP-Logistic shows the strongest dimension sensitivity: runtime grows about 71.8x from `p=5` to `p=100`, and fresh-process peak-RSS delta reaches about 171 MB at `p=100`.

Compact P0-2 through P0-7 records are versioned under `analysis/`. Complete frozen per-repetition tables and the portable computational runner are archived in the cumulative manuscript reproducibility supplement rather than duplicating all raw records into Git history.

## Repository map

```text
synthetic/       locked synthetic runner, tests, primary results, sensitivities
real_data/       UCI acquisition/validation, final runner, directional + radial outputs
analysis/        comparator, estimator, backbone, dimensional, temporal, and compute audits
docs/protocols/  final protocols and accepted amendments
```

## Evidence inventory

| layer | frozen result rows |
|---|---:|
| Synthetic primary | 14,520 |
| Real directional | 2,500 |
| Real radial | 600 |
| P0-2 comparator — synthetic | 3,630 |
| P0-2 comparator — public | 2,500 |
| P0-3 estimator stress — synthetic | 2,850 |
| P0-3 estimator stress — public | 3,200 |
| P0-4 backbone factorial — synthetic | 17,040 |
| P0-4 backbone factorial — public | 3,200 |
| P0-5 high-dimensional weighting stress | 4,320 |
| P0-6 natural temporal deployment validation | 240 |
| P0-7 computational/scalability timing audit | 292 |

Real-data configuration SHA-256: `b1aeef06011ba4c112737e9622f6a5adc477e87e76d36ebad5b6557871b6805a`.

## Quick verification

```bash
python -m pip install -r requirements.txt
python verify_release.py
(cd synthetic && PYTHONPATH=src python -m pytest -q tests/test_v10.py)
(cd real_data && PYTHONPATH=code python -m pytest -q tests)
```

See [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md), [`analysis/p05_highdim`](analysis/p05_highdim), [`analysis/p06_natural_temporal`](analysis/p06_natural_temporal), and [`analysis/p07_computational_scalability`](analysis/p07_computational_scalability). The cumulative manuscript supplement verifies P0-2 through P0-7 and ends with `P0-7 VERIFY: PASS`.

## Data policy

Raw third-party UCI files are not redistributed. The repository provides acquisition code, schema rules, UCI identifiers, canonical SHA-256 values, compact summaries, audit tables, manifests, and executable code. Complete deterministic tables are retained in the manuscript supplement when useful for auditability.

## Scientific provenance

- Synthetic master seed: `2026081601`.
- Real-data master seed: `2026081602`.
- Nominal coverage: `0.90`.
- Persistent undercoverage alarm: mean coverage `< 0.87` for two adjacent positive severities.
- Information-fragility alarm: `ESS / n_cal <= 0.20` for two adjacent positive severities.
- Usability alarm: infinite-interval fraction `>= 0.05` for two adjacent positive severities.
- Primary density-ratio estimator: standardized polynomial logistic domain classifier, `C=0.1`; sensitivity `C=0.01`.
- P0-3 alternatives: histogram-gradient-boosting classifier odds and direct uLSIF.
- P0-4 synthetic backbones: Ridge(alpha=1) and mean GBR; public backbones: Ridge(alpha=1) and HGBR.
- P0-5 predictor isolation: first five signal coordinates fixed for prediction; all `p` coordinates used for weighting.
- P0-6 chronology: 2011-2013 source; 2014/2015 separate natural target years; no engineered tilt.
- P0-7 computation: sequential method-by-axis batches with NumPy/SciPy OpenBLAS and scikit-learn OpenMP verified at one thread; empirical scaling exponents are finite-grid descriptors, not theoretical complexity claims.

Operational thresholds are reproducible stress-test landmarks, not universal theoretical constants.

## Citation

Citation metadata are provided in [`CITATION.cff`](CITATION.cff). Scientific artifact version remains **1.5.0**; P1-3 changes terminology/editorial framing but does not change the numerical evidence.

## Reuse

No separate software license is declared in this archival release. Third-party UCI datasets remain subject to their source terms. For reuse beyond scholarly verification/citation, contact the author.
