Real-Data Benchmark Protocol v1.0 — LOCKED  
Target manuscript: Stress-Testing Conformal Regression Under Progressive Covariate Shift

1\. Purpose  
The real-data layer is a validation benchmark for the failure patterns observed in the locked synthetic experiment. It is not intended to discover a new conformal method or to optimize dataset-specific performance. Dataset selection, preprocessing, shift construction, severity values and primary methods must be fixed before comparative results are inspected.

2\. Primary Dataset Set  
All primary datasets are hosted by the UCI Machine Learning Repository and currently carry CC BY 4.0 licenses.

D1 — Combined Cycle Power Plant  
UCI ID: 294  
DOI: 10.24432/C5002N  
Instances: 9,568  
Predictive features: 4 real-valued ambient variables  
Target: PE (net electrical energy output)  
Official page: https://archive.ics.uci.edu/dataset/294/combined%2Bcycle%2Bpower%2Bplant  
Role: low-dimensional physical regression benchmark.

D2 — Appliances Energy Prediction  
UCI ID: 374  
DOI: 10.24432/C5VC8G  
Instances: 19,735  
Reported features: 28  
Target: Appliances energy use  
Official page: https://archive.ics.uci.edu/dataset/374/appliances%2Benergy%2Bprediction  
Preprocessing: drop date from predictive matrix; drop rv1 and rv2 because the dataset documentation explicitly identifies them as random variables included for model testing. Keep the remaining measured environmental/energy covariates.  
Role: medium-dimensional sensor/environmental benchmark with heterogeneous signal quality.

D3 — Superconductivty Data  
UCI ID: 464  
DOI: 10.24432/C53P47  
Instances: 21,263  
Predictive features: 81  
Target: critical temperature  
Official page: https://archive.ics.uci.edu/dataset/464/superconductivty%2Bdata  
Use train.csv feature table; do not use chemical-formula string fields from unique\_m.csv as predictive variables.  
Role: high-dimensional numerical regression benchmark.

D4 — Gas Turbine CO and NOx Emission Data Set  
UCI ID: 551  
DOI: 10.24432/C5WC95  
Instances: 36,733  
Sensor variables: 11 plus year metadata in the repository representation  
Primary target for this study: NOx.  
Predictors: AT, AP, AH, AFDP, GTEP, TIT, TAT, TEY, CDP. Exclude CO and year from the primary predictor set. CO is excluded to avoid using the second emission response as a proxy target; year is excluded from the feature-based tilt construction.  
Official page: https://archive.ics.uci.edu/dataset/551/gas%2Bturbine%2Bco%2B  
Role: industrial sensor benchmark with process-variable dependence.

D5 — Online News Popularity  
UCI ID: 332  
DOI: 10.24432/C5NS3V  
Canonical instances used: 39,644 (UCI metadata reports 39,797; the official ucimlrepo fetch returns 39,644; documented in amendment v0.3.1).  
Predictive features: 58  
Target: shares  
Official page: https://archive.ics.uci.edu/dataset/332/online%2Bnews%2Bpopularity  
Preprocessing: drop URL and timedelta because the official dataset description labels these as non-predictive. Retain the 58 predictive numeric attributes. Use an affine train-set standardization of y; do not add a post-hoc log transform after viewing comparative results.  
Role: high-dimensional, heterogeneous and strongly non-physical regression benchmark.

Reserve dataset  
Bike Sharing (UCI ID 275; 17,389 hourly records, 13 features) is a reserve only. It will not be added to the primary benchmark unless one of D1–D5 fails a data-integrity or loader reproducibility check before results are inspected.

3\. License and Redistribution Rule  
Dataset metadata, UCI ID, DOI, UCI citation and CC BY 4.0 attribution must be retained in the project manifest. Raw UCI files may be cached locally for reproducibility. The submission repository should prefer a download script \+ checksums rather than republishing raw datasets unnecessarily.

4\. Dataset Acquisition Lock  
Primary acquisition route: official ucimlrepo Python client using UCI IDs 294, 374, 464, 551 and 332\.  
Secondary recovery route: official UCI static download URLs only.  
After download, write a local immutable canonical CSV for each dataset and record SHA-256, row count, column count, target column and dropped columns in dataset\_manifest.json.  
No Kaggle mirror or third-party repackaging is permitted for the primary study.

5\. General Preprocessing  
All split/randomization operations use fixed reproducible seeds.  
No target-based row filtering is allowed.  
Rows with missing predictor/target values: if unexpectedly present despite repository metadata, report count and use complete-case removal only if fewer than 1% of rows; otherwise stop and issue a protocol amendment before analysis.  
Numeric predictors are standardized with StandardScaler fitted on the model-training source subset only.  
Targets are standardized affinely using mean and standard deviation from the model-training source subset. Coverage is invariant to this affine transform; reported application-scale intervals may be inverse-transformed for interpretability.  
No feature selection based on y is allowed.

6\. Repeated Source/Reservoir Split  
Primary repetitions: 20 paired repetitions per dataset.  
Master seed: 2026081602\.  
For every repetition, randomly partition the original rows without replacement:  
• model-training source: 40%  
• calibration source: 25%  
• target reservoir: 35%  
The partition is generated before any shift severity is applied and is shared across all methods and all severity levels within the repetition.

Minimum-size guardrail:  
All five selected datasets exceed the size needed for these fractions. If a loader produces fewer than 8,000 usable rows for a selected dataset, stop that dataset before analysis and investigate rather than silently changing fractions.

7\. Primary Real-Data Shift Construction — Directional Exponential Tilt  
This construction uses X only; y is never used to choose the target domain.

Step A — Fit unsupervised direction  
On standardized training-source X, fit PCA and retain only the first principal component direction v1.

Step B — Define a standardized feature-only shift score  
For any x, compute raw score r(x)=v1^T z(x), where z(x) is training-scaler standardized X.  
Center and scale r using the training-source score mean and SD.  
Clip the resulting score to \[−3,3\] before exponential weighting to prevent a tiny number of empirical points from dominating solely because of numerical overflow.  
Call the clipped standardized score s(x).

Step C — Define target family  
For severity lambda,  
q\_lambda(x) ∝ p(x) exp(lambda s(x)).  
The analytic oracle importance weight relative to the empirical source distribution is proportional to exp(lambda s(x)); normalization is estimated from source calibration weights in the same deterministic manner for all methods.

Step D — Locked severity grid  
lambda ∈ {0, 0.5, 1.0, 1.5, 2.0}.  
These values are not tuned per dataset.  
Actual Oracle ESS/n, MMD² and source-target classifier AUC are reported as achieved shift diagnostics.

8\. Target Sampling  
For each dataset/repetition/severity, target-unlabeled and target-test samples are drawn independently with replacement from the target reservoir using probabilities proportional to exp(lambda s(x)).

n\_target\_unlabeled \= 1,000.  
n\_target\_test \= 2,500.  
Sampling with replacement is intentional: it produces independent draws from the finite empirical tilted distribution while keeping evaluation sample size constant across datasets. Record unique-row fraction for both target samples so severe concentration is auditable.

At lambda=0 the target sampler is uniform over the reservoir.

9\. Secondary Real-Data Tail Sensitivity  
To test whether the synthetic tail-fragility pattern transfers, run a reduced secondary path on D1 (Combined Cycle Power Plant) and D3 (Superconductivity) only.

Define a feature-only radial score from standardized X:  
r\_tail(x) \= ||z(x)||² / p.  
Standardize using training-source mean/SD and clip to \[−3,3\].  
Define q\_lambda,tail(x) ∝ p(x) exp(lambda s\_tail(x)).  
Locked lambda subset: {0,1,2}.  
This is a sensitivity layer, not part of the primary five-dataset directional benchmark.

10\. Locked Methods  
Use the same methodological identities as the synthetic study:  
M1 SCP-Ridge.  
M2 CQR-GBR.  
M3 Estimated-WCP-Primary: polynomial degree 2 \+ logistic density-ratio classifier, C=0.1.  
M4 Oracle-WCP-Ridge: uses the known exponential-tilt oracle weight.  
M5 Estimated-WCP-Sensitivity: degree 2 \+ logistic C=0.01.

No dataset-specific model hyperparameter tuning using shifted test coverage is permitted.

11\. High-Dimensional Weight-Estimation Guardrail  
The polynomial density-ratio feature map is kept consistent with the synthetic methodology. Before the real benchmark is locked, perform a runtime/memory smoke on D3 and D5. If the full degree-2 map cannot be executed reliably, the only permitted modification is a documented unsupervised PCA compression fitted without y and fixed globally for all datasets before the main real-data results are viewed. Such a change requires protocol v0.2 and cannot be made dataset-by-dataset.

12\. Real-Data Metrics  
Validity:  
• empirical coverage  
• one-sided coverage deficit relative to 0.90  
• absolute coverage gap

Information/support:  
• estimated and oracle ESS/n\_cal  
• weight CV  
• maximum normalized weight  
• held-out source-target AUC  
• oracle-estimated log-weight RMSE/MAE/correlation  
• Estimated-WCP minus Oracle-WCP coverage

Usability:  
• infinite-interval fraction  
• finite mean/median interval width  
• finite proper interval score with infinite-fraction reported alongside it

Shift characterization:  
• RBF MMD²  
• achieved oracle ESS/n  
• target unique-row fraction

13\. Real-Data Failure Definitions  
Use the synthetic definitions without retuning:  
Coverage lower acceptable bound \= 0.87.  
Persistent B\_cov requires two consecutive positive lambda levels below 0.87.  
B\_info threshold ESS/n\_cal ≤ 0.20 for two consecutive positive lambda levels.  
B\_inf threshold infinite-interval fraction ≥ 0.05 for two consecutive positive lambda levels.  
Baseline lambda=0 issues are separate quality flags and never called a shift breakpoint.

Because real-data repetitions reuse one finite dataset, interpretation of breakpoint uncertainty must emphasize resampling variability rather than population-level theorem claims.

14\. Rank-Instability Analysis  
Use the same metric-specific logic as the synthetic layer:  
primary ordering by one-sided coverage deficit;  
secondary absolute coverage gap;  
infinite-interval fraction;  
finite interval score only where all methods being compared have zero infinite-interval frequency.  
Report pairwise reversals versus lambda=0 and Kendall tau with ties handled explicitly.

15\. Primary Real-Data Hypotheses  
R1. Shift-induced calibration degradation will vary substantially across datasets; no method will be uniformly dominant.  
R2. Oracle reweighting will generally control coverage better than unweighted baselines as the directional tilt strengthens, but may lose effective calibration information and/or usability.  
R3. Estimated-WCP performance will approach Oracle-WCP in some datasets but diverge in others, with the divergence related to direct weight-fidelity diagnostics rather than ESS alone.  
R4. Synthetic three-axis failure separation will recur in at least a subset of real datasets.  
R5. Method ordering will exhibit severity-dependent reversals and will differ between validity and usability criteria.

16\. Computational Plan  
Primary directional benchmark:  
5 datasets × 5 lambda levels × 20 repetitions \= 500 paired dataset-shift repetitions before method rows.  
Secondary radial sensitivity:  
2 datasets × 3 lambda levels × 20 repetitions \= 120 paired repetitions.

Implement dataset-level and repetition-level sharding. Cache preprocessing and target-weight construction per paired condition so conformal methods share identical data and shift realizations.

17\. Prelock Gates  
This protocol may advance to v1.0 only after:  
• all five official loaders produce expected rows/columns and target definitions;  
• SHA-256 dataset manifest is written;  
• lambda=0 calibration smoke passes on all five datasets;  
• D3/D5 density-ratio memory/runtime smoke passes;  
• oracle exponential weights are unit-tested against direct finite-reservoir normalization;  
• target sampling unique-row diagnostics are verified;  
• no target/y-based selection is introduced;  
• a complete 2-dataset × 3-lambda smoke executes end-to-end.

18\. Current Status  
DATASET SELECTION: LOCKED.  
LICENSE CHECK: PASSED for the five selected UCI datasets.  
SHIFT CONSTRUCTION: LOCKED.  
REAL-DATA RESULTS: GENERATED, MERGED, AND AUDITED.  
The protocol is locked. Comparative results were interpreted only after the directional and radial runs were complete and integrity gates passed.

19\. v0.2 PRELOCK Amendment — Density-Ratio Estimation Independence and High-Dimensional Stability

Reason  
A pre-result, outcome-free high-dimensional estimator screen showed that applying the synthetic study’s full degree-2 polynomial logistic density-ratio model to 58–81 dimensional real-data feature spaces can generate extreme out-of-sample weight dispersion even under null shift. In an 81D null-shift smoke, full-poly2 configurations produced ESS/n values near 0.003–0.016 despite held-out domain AUC near 0.5. This is an estimator-instability problem, not evidence of real shift.

This amendment is made before any real-data comparative conformal result is generated.

19.1 Density-ratio training independence  
Estimated density-ratio models MUST NOT be fitted on the same source calibration rows whose conformity scores receive the estimated weights.

For every dataset/repetition/severity:  
• draw exactly 1,000 density-source X rows without replacement from the model-training source partition;  
• use all 1,000 target-unlabeled X rows as the target class;  
• fit the domain classifier on these balanced feature-only samples;  
• predict weights out-of-sample on calibration X and target-test X.

The source density-fit row selection uses a deterministic seed derived from master seed, dataset ID and repetition and is held fixed across severities where logically possible. No y values enter density-ratio fitting.

19.2 Real-data primary density-ratio estimator  
Supersede the polynomial estimator wording in Section 10 for the real-data layer only.

Primary Estimated-WCP estimator:  
StandardScaler \+ linear LogisticRegression, C=0.1, balanced 1,000-source / 1,000-target-unlabeled domain sample.

Sensitivity estimator:  
StandardScaler \+ linear LogisticRegression, C=0.01, same rows and preprocessing.

The synthetic locked experiment remains unchanged and continues to use its previously locked estimator. This is a real-data implementation decision made before real outcomes are observed.

19.3 Why linear is scientifically appropriate for the primary real-data shift  
The primary real-data target construction is q\_lambda(x) proportional to p(x) exp(lambda s(x)), where s(x) is a standardized linear PC1 score. Therefore the true log density ratio is linear in the predeclared feature-space shift score. A linear logistic density-ratio model is aligned with the primary shift family and avoids unnecessary high-order interaction parameters.

The secondary radial tail sensitivity is intentionally more challenging and may be misspecified for a linear classifier; Oracle-WCP remains available there and the oracle-estimated gap is part of the planned analysis.

19.4 Pre-result estimator-screen evidence  
Outcome-free screens used synthetic X only and did not use any selected real dataset y.

Findings:  
• full 81D polynomial degree-2 map expands to 3,402 classifier features and can severely overfit weights under null shift;  
• full linear models avoid this catastrophic behavior;  
• across synthetic protocol-like dimensions p in {4,9,28,58,81}, C=0.1 had the lowest average non-null log-weight RMSE overall, while C=0.01 provided a more regularized high-dimensional sensitivity condition;  
• dimension-specific C selection is prohibited; the global primary remains C=0.1 and global sensitivity remains C=0.01.

19.5 Additional prelock baseline gates  
At lambda=0 for every real dataset before the main real-data run:  
• held-out domain AUC must be reported and should be statistically compatible with no useful discrimination;  
• estimated calibration ESS/n must be reported;  
• Estimated-WCP baseline coverage and infinite-interval fraction must be audited;  
• failure of a baseline audit triggers investigation/amendment, not automatic hyperparameter tuning.

19.6 Status  
REAL-DATA PROTOCOL v1.0: LOCKED.  
DENSITY-RATIO ARCHITECTURE: LOCKED.  
REAL COMPARATIVE RESULTS: COMPLETE AND AUDITED.

20\. v1.0 FINAL LOCK — Executed Real-Data Benchmark

Execution status  
The real-data layer is complete. The primary directional benchmark contains 5 datasets × 5 severity levels × 20 paired repetitions × 5 methods \= 2,500 method-result rows and 500 seed rows. The prespecified radial sensitivity contains 2 datasets × 3 severity levels × 20 paired repetitions × 5 methods \= 600 method-result rows and 120 seed rows. Both merged outputs use config hash b1aeef06011ba4c112737e9622f6a5adc477e87e76d36ebad5b6557871b6805a. No duplicate condition keys or missing critical coverage/ESS values were found. All lambda=0 baseline gates passed.

Dataset-integrity amendment  
Online News Popularity is retained as a primary dataset. UCI metadata reports 39,797 instances, whereas the official ucimlrepo fetch used by the locked acquisition route returns data.original with 39,644 rows. The canonical benchmark therefore uses 39,644 rows, predictive feature count 58, and SHA-256 e70a03997c3e568a39508e39489aea4088e18436f18cbb8139f7f6ace45f53f0. This mismatch was documented before comparative interpretation; no third-party mirror was introduced.

Primary directional findings  
Persistent SCP-Ridge coverage breakpoints occurred for CCPP (lambda=1.5), Gas Turbine NOx (1.5), Online News (1.5), and Superconductivity (0.5), but not Appliances. Oracle-WCP-Ridge had no directional coverage breakpoint. Information breakpoints occurred for all three weighted conditions in Appliances at lambda=1.5 and for Estimated-WCP-Primary in Online News at lambda=1.5. No directional usability breakpoint occurred at the locked 0.05 infinite-interval threshold.

Radial sensitivity findings  
No radial coverage or usability breakpoint occurred for CCPP or Superconductivity. Superconductivity Estimated-WCP-Primary crossed the information threshold at lambda=1.0. At lambda=2, CCPP Oracle-WCP coverage was 0.90394 with ESS/n=0.05460; Primary Estimated-WCP coverage was 0.88160 and differed from Oracle by \-0.02234 (95% CI \-0.03248 to \-0.01220). For Superconductivity at lambda=2, Oracle-WCP coverage was 0.90046 and SCP-Ridge was conservative at 0.96140; absolute coverage gap therefore favors Oracle even though Oracle coverage is numerically lower.

Final hypothesis audit  
R1 Supported: calibration degradation varies materially across datasets and no method is uniformly dominant across criteria.  
R2 Partially supported: oracle reweighting generally improves coverage control/absolute calibration relative to unweighted SCP under directional shift and can preserve validity under radial stress, but it does not uniformly dominate CQR and the real-data runs did not reproduce the synthetic infinite-interval usability failure.  
R3 Strongly supported: estimated weighting approaches Oracle in several conditions but diverges in others. Online News directional lambda=2 shows Primary-minus-Oracle coverage \+0.0289 (95% CI \+0.0126 to \+0.0452) with log-weight RMSE about 1.83. Across 24 positive-shift dataset-mode-severity condition means from both real-data paths, absolute Estimated-vs-Oracle coverage divergence is more strongly associated with log-weight RMSE (Spearman rho about 0.69) than with estimated ESS alone (rho about \-0.39).  
R4 Partially supported: coverage and information/support failures separate on real data, but the locked 0.05 infinite-interval usability breakpoint does not occur in either the directional or radial layer. This negative result is retained; no post-hoc stress path or threshold change is introduced.  
R5 Supported: severity- and metric-dependent method-order reversals occur in both the directional and radial layers.

Lock decision  
REAL-DATA BENCHMARK v1.0: LOCKED.  
DIRECTIONAL RESULTS: FINAL.  
RADIAL SENSITIVITY: FINAL.  
FAILURE THRESHOLDS: UNCHANGED FROM PRELOCK.  
DENSITY-RATIO C VALUES: UNCHANGED FROM PRELOCK.  
NO FURTHER DATASET-, METHOD-, SEVERITY-, OR THRESHOLD-TUNING IS PERMITTED FOR THE PRIMARY MANUSCRIPT RESULTS.  
