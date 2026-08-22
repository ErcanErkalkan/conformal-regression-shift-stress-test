# P0-5 High-Dimensional Nuisance-Coordinate Stress Audit

## Purpose
P0-5 addresses the remaining low-dimensional synthetic limitation without changing the frozen P0-4 core. It is a post-freeze sensitivity layer designed to isolate the effect of covariate dimension on density-ratio estimation and weighted conformal usability.

## Confound-control rule
A preliminary implementation allowed nuisance coordinates to enter the Ridge predictor. That implementation was rejected before final interpretation because it mixed predictor degradation with weighting degradation. The final P0-5 design fixes the predictor and conformal residual score to the first five true signal coordinates for every dimension. Oracle and estimated density ratios alone see the full p-dimensional covariate vector. No preliminary result is used in the manuscript or frozen P0-5 output.

## Final design
- Dimensions: p = 5, 20, 50, 100.
- Added coordinates: pure Gaussian nuisance covariates for prediction.
- Response/noise: linear-Gaussian, depending only on the first five coordinates.
- Shift families: mean, variance, shifted-component mixture, tail mixture; all retain analytic density ratios.
- Severity anchors: delta = 0, 1, 2.
- Repetitions: 30 paired repetitions.
- Samples per repetition: 1000 train, 1000 calibration, 2500 test, 1000 unlabeled target.
- Nested design: the same 100-dimensional latent rows are sliced to lower p, and mixture indicators are shared across dimensions.
- Predictor: Ridge(alpha=1) fit on first five coordinates only.
- Estimated ratio: locked degree-2 polynomial logistic classifier odds, C=0.1, max_iter=400, using all p covariates.
- Oracle ratio: exact q_X/p_X using all p covariates.

The degree-2 expansion contains 20, 230, 1325, and 5150 features at p=5, 20, 50, and 100, respectively.

## Frozen QA
- Raw rows: 4,320.
- Duplicate condition keys: 0.
- Coverage outside [0,1]: 0.
- Unique estimated-ratio fits after shared zero-shift computation: 1,080.
- Recorded optimizer non-convergence: 0/1,080.
- Independent repetition-0 deterministic rerun: exact numerical match excluding wall-clock timing; maximum absolute difference 0.0 (tolerance 1e-12).

## Main findings
1. Estimated-WCP accumulated undercoverage worsens from p=5 to p=100 in all four analytic families; every paired 95% CI for the p100-p5 A_cov difference excludes zero.
2. The corresponding oracle-WCP A_cov difference includes zero in all four families, separating ratio-estimation degradation from the known-weight coverage-transfer result.
3. At the true zero-shift anchor and p=100, held-out domain AUC remains at chance (0.4982), yet the estimated calibration ESS ratio is 0.00843, analytic log-weight RMSE is 5.6609, and Estimated-WCP coverage is 0.8373. Domain AUC therefore does not validate high-dimensional importance weights.
4. Under p=100 variance shift at delta=2, known-ratio WCP reaches coverage 0.99992 but produces unbounded intervals with frequency 0.99984. Coverage alone is therefore unusable as an operational criterion.
5. Under p=100 tail-mixture shift at delta=2, oracle calibration ESS ratio is approximately 1.0 while 0.29983 of intervals are unbounded. Calibration ESS can look benign while test-point self-weight creates usability failure.

## Evidential status
P0-5 is a post-freeze dimensionality sensitivity. Its three-point severity path is compared only within P0-5 and is not numerically substituted into the locked five-point p=5 core tables. The linear-Gaussian response and predictor restriction are deliberate isolation choices, not claims of exhaustive high-dimensional coverage across all response/noise mechanisms.
