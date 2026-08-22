# P0-2 contemporary comparator expansion

This analysis layer adds two shift-aware conformal comparators without modifying the frozen core benchmark.

## Method-label clarification

The evaluated kernel-mean-matching comparator is **KMM-WCP-Ridge**: non-selective classical RBF kernel mean matching followed by a weighted absolute-residual conformal cutoff. Historical frozen CSV/JSON outputs use the string `KMM-CP-Ridge`; those immutable strings are retained for checksum continuity. They map to `KMM-WCP-Ridge` in the journal manuscript. This implementation is distinct from the published **selective KMM-CP** procedure of Laghuvarapu, Deb, and Sun (UAI 2026).

## Methods

- **KMM-WCP-Ridge** (historical frozen label `KMM-CP-Ridge`): RBF kernel mean matching with bound `B=30`, deterministic bandwidth selection, projected-FISTA optimization, and a weighted absolute-residual conformal cutoff.
- **RLCP-Ridge**: Gaussian randomly localized conformal prediction following Hore & Barber (JRSS-B 2025, DOI `10.1093/jrsssb/qkae103`), using the same Ridge residual score as SCP. The localization bandwidth is selected from source features only to target median local effective size 200.

## Design

- Synthetic: nonlinear response + heteroscedastic noise, all five locked shift families, all 30 repetitions, severities `0, 0.5, 1, 1.5, 2`.
- Public: all five directional UCI datasets, all 20 repetitions, same severity grid.
- Common external budget: `n_cal=1000`, `n_test=1000`, unlabeled-target `n=1000` for every method in this layer.
- External-layer values are not substituted into the larger frozen core tables.

## Main result

KMM-WCP lowers paired pathwise undercoverage area relative to SCP with 95% intervals excluding zero on 4/5 synthetic shift families and 4/5 public datasets. RLCP shows the same 4/5 + 4/5 pattern with smaller reductions. KMM-WCP generally remains behind the known-ratio/known-tilt reference, and RLCP is farther behind on the difficult paths. This is consistent with the mechanisms: KMM-WCP targets RKHS moment balance, RLCP targets randomized localization, while controlled WCP directly uses the shift-weight mechanism.

## QA

- Synthetic KMM solves: 750; maximum projected-gradient residual `9.99844381631712e-05`.
- Public KMM solves: 500; maximum projected-gradient residual `9.985659103244988e-05`.
- No retained KMM solve exceeds the declared `1e-4` tolerance.
- Raw rows: 3,630 synthetic and 2,500 public.
- Path-area rows: 750 synthetic and 500 public.

## Diagnostic comparability

RLCP local effective size is a localization diagnostic, not importance-weight ESS. Therefore RLCP `ess_ratio`, `information_loss`, and `A_info` are intentionally `NA` and are not pooled with WCP/KMM information-concentration metrics.

Raw third-party UCI files are not redistributed; use the repository's existing UCI acquisition/validation workflow and set `P02_DATA_DIR` when running the comparator script.