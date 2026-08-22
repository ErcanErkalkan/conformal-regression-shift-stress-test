# P0-3 density-ratio estimator-family expansion

Status: post-freeze sensitivity; the locked primary estimator and core comparisons are unchanged.

## Question

Does the estimated-WCP fragility observed in the locked benchmark depend on the single linear-logistic domain classifier, or does it persist when the ratio-estimation mechanism changes?

## Estimators

- `Estimated-WCP-Logit`: locked standardized linear logistic classifier odds.
- `Estimated-WCP-HGB`: nonlinear histogram gradient boosting classifier odds, with domain-only early stopping.
- `Estimated-WCP-uLSIF`: direct least-squares importance fitting with 80 RBF centers and a predeclared sigma/lambda grid selected by source + unlabeled-target ratio risk only.

No response outcome or conformal test result is used to tune HGB or uLSIF.

## Design

Synthetic layer: nonlinear response + heteroscedastic noise, all five shift families, 30/30 locked repetitions.

Public layer: all five UCI datasets, 20/20 repetitions, both the directional grid `{0, 0.5, 1, 1.5, 2}` and radial grid `{0, 1, 2}`. The same Ridge-WCP wrapper and locked split/draw streams are reused.

Frozen P0-3 evidence contains 2,850 synthetic method-result rows and 3,200 public method-result rows. The manuscript supplement includes the full frozen raw tables, paired path contrasts, QA records, exact dependency-source snapshots, and an independent verifier.

## Main result

There is no globally best ratio estimator. HGB improves construction-reference weight fidelity across all five public radial datasets in point estimate, significantly on four, but this does not monotonically improve one-sided undercoverage. uLSIF can retain high effective sample size while producing poor reference-weight agreement and poor coverage; on all five synthetic shift families it has lower `A_info` than logistic but larger `A_cov`.

This is why `A_cov`, absolute coverage gap, ESS/concentration, reference-weight discrepancy, and interval usability are reported separately.

## Repository execution

Use:

```bash
python analysis/p03_density_estimator_expansion/run_p03_repo.py --smoke
```

for a one-repetition smoke test, or omit `--smoke` for the full run. Canonical public CSVs must be reconstructed through the repository's UCI acquisition/validation workflow. The manuscript supplement `Reproducibility_Supplement_P0_3.zip` is the archival, self-verifying P0-3 package.
