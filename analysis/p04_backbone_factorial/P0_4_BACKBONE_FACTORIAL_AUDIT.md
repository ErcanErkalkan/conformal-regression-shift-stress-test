# Neurocomputing P0-4 Backbone-Factorial Audit - v0.29

## Objective
Close the remaining predictive-backbone confounding risk by separating conformal-wrapper effects from predictor effects, while leaving all locked primary results unchanged.

## Design
### Synthetic
- 30/30 paired repetitions; master seed and source/target draws unchanged.
- Full locked severity grid {0, 0.5, 1.0, 1.5, 2.0}.
- SCP and known-ratio WCP crossed with Ridge(alpha=1) and the earlier mean-GBR sensitivity model (80 trees, learning rate 0.1, max depth 3).
- Factorial WCP inference restricted to the four analytic-ratio shift families (16 DGP/noise/family profiles).
- Separate CQR family sensitivity: unpenalized linear 0.05/0.95 quantile regression versus locked CQR-GBR.

### Public
- 5/5 UCI datasets, 20/20 paired repetitions.
- Both directional and radial controlled tilts; main target-test size 2500 retained.
- SCP and construction-reference WCP crossed with Ridge and HistGradientBoostingRegressor.
- HGBR is used for the public second backbone because classical GBR showed prohibitive runtime on high-dimensional Superconductivity. The HGBR configuration was fixed before reported public factorial outcomes and not tuned on coverage.

## QA
- Synthetic rows: 17,040; exactly 568 rows per repetition.
- Public rows: 3,200; exactly 160 rows per repetition.
- Duplicate keys: 0 synthetic, 0 public.
- Coverage values outside [0,1]: 0.
- Deterministic rep-0 recheck: max numeric difference 7.11e-15 synthetic and 2.22e-16 public CCPP; keys identical.
- Earlier M7 checkpoint reproduced: difficult-condition SCP-Ridge 0.5959867; SCP-GBR 0.6438400.

## Main results
### Synthetic analytic profiles
- Persistent coverage failures: SCP-Ridge 10/16; SCP-GBR 14/16; Oracle-WCP-Ridge 0/16; Oracle-WCP-GBR 0/16.
- SCP backbone A_cov effect (GBR - Ridge): 8 significantly positive, 8 significantly negative, 0 including zero.
- WCP backbone A_cov effect: 0 positive, 0 negative, 16 including zero.
- Wrapper x backbone A_cov interaction: 8 positive, 8 negative, 0 including zero.
- The interaction sign follows response structure: all eight linear-response profiles and all eight nonlinear-response profiles lie on opposite sides of zero.
- CQR-GBR minus CQR-Linear A_cov: 3 positive, 6 negative, 7 including zero; mean difference -0.0092.

### Public directional + radial paths
- Persistent coverage failures: SCP-Ridge 6/10; SCP-HGBR 4/10; Known-tilt-WCP-Ridge 0/10; Known-tilt-WCP-HGBR 0/10.
- SCP backbone A_cov effect (HGBR - Ridge): 0 positive, 7 negative, 3 including zero.
- WCP backbone A_cov effect: 0 positive, 0 negative, 10 including zero.
- Wrapper x backbone A_cov interaction: 7 positive, 0 negative, 3 including zero.

## Interpretation
The magnitude of the apparent WCP-versus-SCP correction gain is backbone-dependent because the unweighted SCP trajectory changes with the predictor. In contrast, the tested known-weight WCP accumulated-undercoverage path is substantially more stable across the two backbones. Therefore P0-4 removes the earlier basis for attributing SCP-vs-WCP differences solely to the conformal wrapper, while strengthening the narrower claim that known-weight coverage transfer is not a Ridge-specific artifact in these stress constructions.

CQR remains a complete-pipeline comparator rather than a cell in the exact 2x2 factorial because changing from mean regression to quantile regression also changes the training objective. The separate CQR model-family sensitivity makes this limitation explicit rather than hiding it.

## Locked-core integrity
No locked primary seed, split, target draw, threshold, primary method, primary hyperparameter, or primary result was changed. P0-4 is a post-freeze sensitivity layer.

## Status
**P0-4: PASS.**
