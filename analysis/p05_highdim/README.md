# P0-5 — High-dimensional nuisance-coordinate stress

P0-5 isolates the effect of covariate dimension on density-ratio weighting without changing the predictive signal seen by the conformal predictor.

## Design

- Dimensions: `p = {5, 20, 50, 100}`.
- Shift families: mean, variance, mixture, tail mixture.
- Severity anchors: `0, 1, 2`.
- Paired repetitions: `30`.
- Train/calibration/test/unlabeled-target sizes: `1000 / 1000 / 2500 / 1000`.
- The Ridge predictor and conformity score always use only the first five signal coordinates.
- Oracle and estimated density ratios use all `p` covariates.
- Estimated ratio: degree-2 polynomial logistic classifier odds, `C=0.1`, max 400 iterations.

This is a post-freeze dimensionality sensitivity. It does not replace the locked five-severity `p=5` core benchmark.

## Main findings

Estimated-WCP accumulated undercoverage worsens significantly from `p=5` to `p=100` in all four analytic shift families, whereas the corresponding Oracle-WCP `A_cov` differences include zero in all four families.

The zero-shift negative control is particularly informative: at `p=100`, held-out domain AUC is approximately `0.498`, yet Estimated-WCP coverage falls to approximately `0.837`, calibration ESS ratio to `0.00843`, and analytic log-weight RMSE rises to approximately `5.66`. Thus chance-level discrimination does not certify useful importance weights in the high-dimensional polynomial-logistic pipeline.

At `p=100`, variance shift with severity 2 yields near-unit Oracle-WCP coverage but almost entirely unbounded intervals; tail-mixture severity 2 has oracle calibration ESS near one while about 30% of intervals are unbounded. These cases reinforce the separation between coverage, calibration-weight concentration, and interval usability.

## Files

- `run_p05_highdim.py`: deterministic repetition runner.
- `analyze_p05.py`: merges 30 repetition outputs and computes path areas, paired dimension contrasts, scaling summaries, and QA.
- `P0_5_HIGHDIM_AUDIT.md`: frozen audit and scientific interpretation.
- `results/`: compact frozen outputs only. The complete 4,320-row raw table is archived in the manuscript reproducibility supplement rather than duplicated into Git history.

The cumulative manuscript supplement verifies P0-2 through P0-5 and ends with `P0-5 VERIFY: PASS`.
