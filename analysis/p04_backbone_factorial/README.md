# P0-4 Backbone-Factorial Extension

This layer separates conformal-wrapper and predictive-backbone effects without altering the locked core benchmark.

## Design

Synthetic factorial core (30 paired repetitions):
- wrappers: ordinary split conformal (SCP) and known-ratio weighted conformal (WCP),
- backbones: Ridge(alpha=1) and the pre-existing mean GradientBoostingRegressor sensitivity (80 estimators, learning rate 0.1, depth 3),
- all five locked severity points; factorial inference uses the four analytic-ratio shift families,
- separate CQR model-family sensitivity: CQR-Linear versus the locked CQR-GBR.

Public factorial extension (20 paired repetitions, all 5 datasets):
- wrappers: SCP and construction-reference known-tilt WCP,
- backbones: Ridge and HistGradientBoostingRegressor,
- both locked directional and radial tilt geometries,
- 2500 target-test observations per condition, matching the main public configuration.

The public second backbone is HGBR because the classical GBR used in the synthetic M7 sensitivity scales poorly on the 81-feature Superconductivity dataset. The public HGBR configuration was fixed before the reported factorial results and is not tuned on coverage outcomes.

## Primary factorial estimand

For pathwise accumulated one-sided coverage deficit `A_cov`, the interaction is

`(WCP_second - SCP_second) - (WCP_Ridge - SCP_Ridge)`.

The same paired structure is also reported for absolute coverage gap and finite interval width.

## Frozen headline checks

- Synthetic analytic profiles: WCP backbone-effect A_cov CI includes zero in 16/16 profiles; SCP backbone effect excludes zero in 16/16 (8 positive, 8 negative); interaction is 8 positive / 8 negative.
- Public dataset-geometry paths: WCP backbone-effect A_cov CI includes zero in 10/10; SCP backbone effect is significantly negative in 7/10 and includes zero in 3/10; interaction is significantly positive in 7/10 and includes zero in 3/10.
- Persistent undercoverage: synthetic SCP Ridge/GBR = 10/16 vs 14/16; known-ratio WCP = 0/16 under both. Public SCP Ridge/HGBR = 6/10 vs 4/10; known-tilt WCP = 0/10 under both.
- Earlier M7 checkpoint reproduced: nonlinear-heteroscedastic variance shift at severity 2 gives SCP-Ridge 0.5959867 and SCP-GBR 0.6438400 coverage.

## Data

Raw third-party UCI files are not redistributed. Reconstruct the canonical CSVs using the acquisition/validation assets in the frozen real-data source and set `P04_DATA_DIR` to the directory containing `ccpp.csv`, `appliances.csv`, `superconductivity.csv`, `gas_turbine_nox.csv`, and `online_news.csv`.

## Verification

The submission supplement contains the cumulative `verify_p0_4.py` verifier, which first runs inherited P0-2/P0-3 checks and then checks P0-4 frozen outputs and factorial invariants.
