Experiment Protocol v1.0 — LOCKED

Working Study  
Stress-Testing Conformal Regression Under Progressive Covariate Shift: Degradation Profiles, Support-Overlap Breakpoints, and Rank Stability

1\. Experimental Goal  
Quantify how conformal regression methods deteriorate as distribution shift severity increases, determine where practical coverage failure occurs, and test whether method rankings remain stable across different shift families and support-overlap conditions.

2\. Primary Experimental Factors

Factor A — Data-generating function  
F1. Linear  
Y \= βᵀX \+ ε

F2. Smooth nonlinear  
Y \= 2 sin(X1) \+ 0.5 X2² \+ X3X4 \+ ε

F3. Interaction-heavy  
Y \= X1X2 \+ X3X4 \+ 0.5 X5² \+ ε

Factor B — Noise  
N1. Gaussian homoscedastic  
N2. Heteroscedastic  
N3. Heavy-tailed Student-t

Factor C — Shift family  
S0. No shift  
S1. Mean shift  
S2. Variance/covariance shift  
S3. Tail-heaviness shift  
S4. Mixture shift  
S5. Localized subpopulation shift  
S6. Nonlinear feature transformation shift

Factor D — Shift severity  
Initial grid:  
δ ∈ {0, 0.25, 0.50, 0.75, 1.00, 1.50, 2.00}

Factor E — Base regressor  
B1. Ridge regression  
B2. Random Forest  
B3. Gradient Boosting / XGBoost

Factor F — Conformal method  
M1. Standard Split Conformal Prediction  
M2. Conformalized Quantile Regression  
M3. Weighted Split Conformal Prediction with estimated density ratio  
M4. Recent support-overlap-aware method, included only if implementation is reproducible and computationally feasible

3\. Initial Sample Sizes  
Pilot design:  
n\_train \= 1500  
n\_cal \= 750  
n\_test \= 2000

Main design candidate:  
n\_train \= 3000  
n\_cal \= 1500  
n\_test \= 5000

Sample sizes will be stress-tested during pilot work. Final values must permit stable confidence intervals without making the full factorial design impractical.

4\. Nominal Coverage Levels  
Primary:  
1 − α \= 0.90

Sensitivity:  
1 − α ∈ {0.80, 0.90, 0.95}

5\. Progressive Mean-Shift Example  
Source:  
X \~ N(0, I)

Target:  
X\_target \~ N(δv, I)

where v is either:  
• all-features direction,  
• sparse direction affecting selected features,  
• high-importance-feature direction.

This distinction is important because equal Euclidean shift magnitude may have different predictive consequences depending on which features move.

6\. Support-Overlap Stress Design  
A separate experiment will explicitly degrade source-target overlap.

Candidate controls:  
• increasing mean separation,  
• shrinking shared-support region,  
• mixture component appearing only in target,  
• selective feature truncation.

Track:  
• empirical coverage,  
• interval width,  
• interval score,  
• effective sample size (ESS) of importance weights,  
• coefficient of variation of weights,  
• maximum normalized weight,  
• MMD or another distribution discrepancy,  
• target fraction outside reliable source support.

7\. Core Evaluation Metrics

Standard:  
• Empirical coverage  
• Absolute coverage gap  
• Mean interval width  
• Median interval width  
• Proper interval score  
• RMSE / MAE of base predictor

Shift-profile:  
• Coverage-gap curve versus δ  
• Interval-width curve versus δ  
• Interval-score curve versus δ  
• ESS curve versus δ  
• Area under absolute coverage-deviation curve  
• Slope of degradation in prespecified shift ranges

Failure characterization:  
• Practical coverage-failure breakpoint  
• Support-overlap failure point  
• First δ where lower confidence bound for coverage falls below target tolerance

Ranking:  
• Per-condition method rank  
• Kendall τ across shift families  
• Spearman rank correlation  
• Rank variance  
• Pairwise win/loss matrix

All non-standard diagnostic names are provisional until formula-level literature verification is completed.

8\. Practical Coverage Tolerance  
Primary candidate:  
τ \= 0.02

For 90% nominal coverage, practical failure candidate:  
|Ĉ(δ) − 0.90| \> 0.02

Sensitivity:  
τ ∈ {0.01, 0.02, 0.05}

A statistical version will also be evaluated:  
failure if the confidence interval for true coverage is incompatible with the prespecified acceptable region.

9\. Repetitions  
Pilot:  
30 repetitions per condition

Main:  
100 repetitions per condition

If Monte Carlo standard errors remain unstable, increase selectively rather than uniformly.

10\. Statistical Analysis

10.1 Pointwise  
For each condition:  
mean  
standard deviation  
Monte Carlo standard error  
95% confidence interval

10.2 Curve-Level  
Compare degradation trajectories using:  
• integrated absolute coverage deviation  
• integrated interval score  
• bootstrap confidence bands  
• paired differences across identical random seeds

10.3 Breakpoint-Level  
Estimate:  
• median breakpoint  
• bootstrap confidence interval  
• probability of failure by each δ

10.4 Ranking-Level  
Assess:  
• within-shift ranking  
• cross-shift ranking consistency  
• sensitivity of ranking to base regressor  
• sensitivity to α

11\. Randomization and Reproducibility  
Each experiment configuration receives:  
• deterministic configuration ID  
• master seed  
• repetition seed  
• data-generation seed  
• model seed

All raw outputs are appended to a machine-readable result table.

Minimum result schema:  
experiment\_id  
dgp  
noise  
shift\_family  
shift\_severity  
overlap\_level  
base\_model  
conformal\_method  
alpha  
replication  
coverage  
coverage\_gap  
mean\_width  
median\_width  
interval\_score  
rmse  
mae  
ess  
weight\_cv  
max\_weight  
runtime\_seconds

12\. Pilot Experiment Scope  
Do NOT run the full factorial design first.

Pilot subset:  
• F1 Linear \+ F2 Nonlinear  
• N1 Gaussian \+ N2 Heteroscedastic  
• S0 No shift \+ S1 Mean shift \+ one support-overlap shift  
• B1 Ridge \+ B2 Random Forest  
• M1 Split CP \+ M2 CQR \+ M3 Weighted CP  
• δ ∈ {0, 0.5, 1.0, 1.5}  
• 30 repetitions  
• nominal coverage 90%

Pilot success criteria:  
• all pipelines execute end-to-end,  
• no silent NaN/Inf failures,  
• weight diagnostics are logged,  
• coverage behaves plausibly at δ \= 0,  
• shifted conditions create measurable but non-degenerate stress,  
• repeated-run variability is understood.

13\. Real-Data Benchmark Selection Rules  
Choose 4–6 public regression datasets with:  
• at least several thousand samples where possible,  
• mixed dimensionality,  
• different signal-to-noise ratios,  
• reproducible download route,  
• unambiguous target variable,  
• permissive research use,  
• no need for new human-subject intervention.

Real-data shifts should be generated transparently rather than opportunistically cherry-picked.

Candidate mechanisms:  
• covariate-based stratified source/target splits,  
• temporal split where legitimate,  
• quantile-based domain split,  
• synthetic perturbation applied to test covariates with clear documentation.

14\. Computational Scope Guardrail  
The project should remain runnable on a local workstation.

If the full design becomes too large:  
Priority 1 — preserve number of shift families  
Priority 2 — preserve repeated runs  
Priority 3 — preserve conformal-method diversity  
Priority 4 — reduce number of base regressors  
Priority 5 — reduce grid density while keeping progressive severity ordering

15\. Experiment Lock Criteria  
Protocol may be labeled v1.0 only when:  
• novelty review is sufficiently mature,  
• all primary metrics are frozen,  
• shift generators are mathematically specified,  
• pilot code passes reproducibility tests,  
• method implementations are validated against known no-shift behavior,  
• result schema is frozen,  
• computational budget is measured.

16\. Immediate Coding Order  
Step 1\. Configuration schema  
Step 2\. Synthetic data generators  
Step 3\. Shift generators  
Step 4\. Base regressors  
Step 5\. Split CP baseline  
Step 6\. CQR baseline  
Step 7\. Weighted CP baseline  
Step 8\. Metrics and weight diagnostics  
Step 9\. Pilot runner  
Step 10\. Aggregation and plotting

17\. Protocol v0.2 Amendment After Executable Pilot

Pilot v0.1 completed successfully with 30 repetitions under Gaussian mean shift. The v0.2 protocol supersedes any wording that implies a single universal failure breakpoint.

17.1 Failure dimensions

B\_cov — Coverage-failure breakpoint  
Operational definition: the first severity value at which mean empirical coverage is below the prespecified acceptable lower bound for m consecutive severity levels. Primary pilot candidate: nominal 0.90, tolerance ε \= 0.03, persistence m \= 2\. Sensitivity analysis must evaluate ε ∈ {0.01, 0.02, 0.03, 0.05}. A second inferential definition will use confidence intervals rather than only the mean.

Information/support fragility profile  
Report ESS, ESS/n\_cal, coefficient of variation of importance weights, maximum normalized weight, and where feasible an explicit source-target discrepancy statistic. ESS is explanatory and established in prior literature; it is not a proposed new metric.

B\_use — Usability/efficiency breakpoint  
Do not use a single universal threshold. Candidate operational events include: non-zero/increasing infinite-interval fraction for weighted conformal methods, prespecified inflation of proper interval score relative to the no-shift baseline, and severe interval-width inflation. Any threshold must be fixed before the main run and accompanied by threshold sensitivity analysis.

17.2 Multi-axis failure interpretation

A method may preserve marginal coverage while simultaneously losing effective calibration information or producing practically uninformative intervals. Therefore every main figure/table that reports coverage under shift should be paired with at least one informativeness/fragility diagnostic.

17.3 Ranking definition

Primary ranking statistic should use a proper interval score rather than raw interval width alone. Coverage will be reported separately and used as a validity constraint/diagnostic. Rank stability analysis must handle ties explicitly. Report pairwise order changes, Kendall tau/Spearman correlation where meaningful, and the number/proportion of rank reversals across severity levels and shift families.

17.4 Pilot v0.1 evidence informing v0.2

At severity δ \= 2.0 in the first mean-shift pilot, SCP-Ridge undercovered strongly (mean coverage about 0.731), CQR-GBR also undercovered (about 0.789), while Oracle-WCP-Ridge remained conservative (about 0.928). However, the weighted calibration ESS fell to about 40 out of 600 and the mean infinite-interval fraction rose to about 0.144. This demonstrates why coverage and usability/support fragility must be separated.

17.5 Shift-family expansion order

Pilot v0.2 coding order:  
1\. Mean shift — retain as regression test and oracle-weight validation case.  
2\. Variance/covariance shift — include a mathematically exact density ratio where feasible.  
3\. Heavy-tail shift — evaluate coverage degradation; weighted correction only if a valid density ratio is specified and numerically stable.  
4\. Mixture/localized shift — explicitly create support-overlap deterioration.  
5\. Nonlinear feature transformation shift — use as a robustness/stress case, not necessarily as a weighted-CP oracle case.

17.6 Estimated-weight condition

The main study must distinguish oracle WCP from estimated-weight WCP. Oracle WCP measures the intrinsic effect of correct reweighting under a known shift; estimated WCP measures practical degradation from density-ratio estimation. These conditions must never be pooled.

17.7 Protocol lock rule

Do not advance to protocol v1.0 until: (a) at least four shift families execute end-to-end, (b) the estimated-weight pipeline is validated, (c) rank-reversal logic with ties is tested, (d) failure definitions are frozen before the main experiment, and (e) the novelty review has completed backward/forward citation chasing around the closest 2024–2026 papers.

18\. Protocol v0.3 Amendment — Weight Fidelity, Shift Discrepancy, and Metric-Specific Ranking

18.1 New shift family

Add an analytically tractable heavy-tail stress condition using a zero-centered Gaussian scale mixture. The source remains N(0,I). The target is a mixture of the source Gaussian and a wider zero-centered Gaussian component. The exact target/source density ratio is available, allowing oracle WCP and direct estimated-weight error analysis. This condition is called tail\_mixture and should not be described as a Student-t shift.

18.2 Independent shift-discrepancy coordinate

For every source-target pair, report an estimator-independent RBF MMD² statistic using a pooled median bandwidth heuristic and bounded subsampling for computational control. MMD² is a descriptive distribution-separation coordinate only; it is not a proposed contribution or new metric.

Family-native severity remains the primary intervention parameter. Cross-family comparisons at equal numeric severity are prohibited unless additionally matched/stratified by an empirical discrepancy coordinate.

18.3 Direct weight-fidelity diagnostics

For every shift family with an analytic oracle density ratio, Estimated-WCP must be accompanied by:  
• normalized log-weight RMSE;  
• normalized log-weight MAE;  
• normalized log-weight correlation where variance permits;  
• Estimated ESS / Oracle ESS ratio;  
• Estimated-WCP minus Oracle-WCP coverage;  
• Estimated-WCP minus Oracle-WCP finite interval score;  
• downstream infinite-interval fractions for both conditions.

Weights are normalized to mean 1 before direct error comparison; log weights are robustly clipped only for the error diagnostic, with the clipping rule fixed and reported.

18.4 ESS interpretation rule

A high estimated ESS must never be interpreted by itself as evidence of accurate density-ratio estimation. The v0.3 pilot demonstrates that estimated weights can remain smooth/high-ESS yet produce substantial coverage loss relative to oracle WCP. ESS is a concentration diagnostic, not a fidelity diagnostic.

18.5 Ranking correction

Do not rank all methods by finite-only interval score when any method has non-zero infinite-interval frequency.

Primary rank-instability outputs are metric-specific:  
• absolute coverage gap;  
• one-sided coverage deficit;  
• infinite-interval frequency;  
• other clearly named standard metrics as appropriate.

An optional operational usability ordering may be lexicographic: first minimize infinite-interval frequency, then minimize finite interval score. It must be described as an ordering rule, not as a proper scoring rule or a newly proposed scalar metric.

18.6 v0.3 pilot configuration

Diagnostic pilot executed with:  
• 8 repetitions;  
• n\_train \= 450;  
• n\_cal \= 450;  
• n\_test \= 650;  
• n\_target\_unlabeled \= 450;  
• p \= 5;  
• families \= mean, variance, mixture, tail\_mixture, nonlinear;  
• native severities \= 0, 0.5, 1.0, 1.5, 2.0;  
• methods \= SCP-Ridge, CQR-GBR, Estimated-WCP-Ridge, plus Oracle-WCP-Ridge where the density ratio is analytic.

This is still a diagnostic pilot, not the final Monte Carlo experiment.

18.7 Density-ratio estimator selection gate

Before the 30-repetition pilot, run a dedicated estimator-screening study. Do not silently select one estimator after looking only at final conformal coverage.

Candidate estimator families should include at minimum:  
• regularized linear logistic density-ratio estimation;  
• regularized degree-2 polynomial logistic density-ratio estimation with multiple predeclared regularization strengths.

Selection/evaluation dimensions:  
• null-shift held-out discrimination AUC close to 0.5;  
• null-shift ESS close to n\_cal without requiring exact equality;  
• oracle log-weight error where available;  
• downstream Estimated-WCP vs Oracle-WCP coverage gap;  
• stability across shift families rather than best performance in one family;  
• numerical stability and reproducibility.

Estimator selection must be documented before the main experiment and sensitivity to at least one alternative estimator should remain in the final study.

18.8 v1.0 protocol gate update

Protocol v1.0 additionally requires:  
• density-ratio estimator screening completed and selection rule documented;  
• metric-specific rank analysis verified;  
• tail-mixture generator and oracle ratio tests passing;  
• independent discrepancy coordinate verified;  
• oracle-vs-estimated diagnostic schema frozen.

19\. Protocol v1.0 LOCK — Superseding Main-Experiment Specification

Status  
LOCKED for the primary synthetic experiment. Earlier candidate values in Sections 1–18 remain as development history; when a conflict exists, this Section 19 supersedes them. Any change after this lock requires a numbered amendment that states whether the change fixes a software error, a mathematical specification error, or changes the scientific design.

19.1 Contribution boundary  
The primary contribution is an evaluation/stress-testing protocol, not a new conformal algorithm, coverage theorem, density-ratio estimator, ESS measure, MMD measure, or composite coverage-width score. Novelty language must remain narrow and consistent with the 2026-08-16 novelty audit.

19.2 Locked primary synthetic factors  
Data dimension: p \= 5\.

Primary response mechanisms:  
DGP-L (linear): f(X) \= 1.5X1 − 1.0X2 \+ 0.75X3 \+ 0.50X4 − 0.25X5.  
DGP-N (nonlinear): f(X) \= 2sin(X1) \+ 0.5X2^2 \+ X3X4 \+ 0.5X5.

Primary outcome-noise mechanisms:  
N-G: homoscedastic Gaussian noise, ε \~ N(0,1).  
N-H: heteroscedastic Gaussian noise, ε \~ N(0, σ(X)^2), σ(X)=0.5+0.5|X1|.

Heavy-tailed outcome noise is a secondary sensitivity analysis and is not part of the primary factorial core.

Locked covariate-shift families:  
S1 mean shift;  
S2 isotropic variance shift;  
S3 shifted-component mixture / support-overlap deterioration;  
S4 zero-centered Gaussian tail mixture;  
S5 nonlinear feature-transformation shift.

Locked native severity grid:  
δ ∈ {0, 0.5, 1.0, 1.5, 2.0}.  
Numeric δ values are family-native intervention parameters. Equal numeric δ across different shift families MUST NOT be interpreted as equal physical distributional distance. Cross-family severity interpretation is descriptive and may additionally use MMD² as an explanatory coordinate.

19.3 Locked sample sizes and repetition plan  
Primary core, per paired repetition:  
n\_train \= 1000  
n\_cal \= 1000  
n\_test \= 2500  
n\_target\_unlabeled \= 1000  
repetitions \= 30  
master\_seed \= 2026081601

The same source split, target sample and repetition seed must be reused across methods within a condition. Method comparisons are paired by construction.

Core factorial size before method rows:  
2 DGP × 2 noise mechanisms × 5 shift families × 5 severity levels × 30 repetitions \= 3000 paired condition-repetitions.

The δ=0 distributions are identical across shift-family generators. Implementations may cache/reuse the baseline computation for efficiency, but exported result tables must retain explicit family labels so trajectory analyses remain rectangular and auditable.

19.4 Locked methods  
Primary baselines:  
M1 SCP-Ridge — standard split conformal prediction with Ridge base regression.  
M2 CQR-GBR — conformalized quantile regression using gradient-boosted quantile regressors.  
M3 Estimated-WCP-Primary — weighted split conformal Ridge with classifier density-ratio estimator fixed at polynomial degree 2, logistic C=0.1.  
M4 Oracle-WCP-Ridge — weighted split conformal Ridge using the analytic density ratio when available.

Mandatory estimator sensitivity:  
M5 Estimated-WCP-Sensitivity — polynomial degree 2, logistic C=0.01, evaluated on the same paired samples.

A recent external method such as KMM-CP may be added later as a supplementary benchmark only through an amendment. It may not replace the locked baselines or change the primary hypotheses after results are seen.

19.5 Locked nominal coverage and coverage-failure definition  
Primary nominal coverage: 1−α \= 0.90.  
Primary practical undercoverage tolerance: τ \= 0.03.  
Acceptable lower coverage bound: 0.87.  
Persistence requirement: m \= 2 consecutive severity levels.

Primary coverage-failure breakpoint B\_cov:  
the smallest severity δ\_j such that mean empirical coverage is below 0.87 at δ\_j and remains below 0.87 at the next available severity level.

Important correction:  
B\_cov is based on one-sided coverage deficit, not absolute coverage gap. Conservative overcoverage is NOT classified as coverage failure.

Inferential companion breakpoint B\_cov,CI:  
the smallest severity δ\_j for which the UPPER bound of the 95% confidence interval for mean coverage is below 0.87 at δ\_j and at the next available severity level. Using the lower CI bound for this purpose would be logically incorrect for establishing persistent undercoverage.

Breakpoint sensitivity:  
τ ∈ {0.02, 0.03, 0.05}; m ∈ {1,2} reported as sensitivity, with τ=0.03 and m=2 primary.

19.6 Locked support/information-fragility reporting  
Continuous primary diagnostics:  
ESS;  
ESS/n\_cal;  
coefficient of variation of importance weights;  
maximum normalized calibration weight;  
held-out source-target discriminator AUC for estimated weighting;  
RBF MMD² as an estimator-independent shift-separation coordinate;  
normalized log-weight RMSE/MAE/correlation where oracle weights exist;  
Estimated-WCP minus Oracle-WCP coverage;  
Estimated ESS / Oracle ESS.

Operational information-fragility onset B\_info:  
first severity with mean ESS/n\_cal ≤ 0.20 for two consecutive severity levels.  
Sensitivity thresholds: 0.10 and 0.30.  
This threshold is an operational reporting convention, not a theorem and not a proposed new metric.

19.7 Locked usability reporting  
Primary usability indicator for weighted methods: infinite-interval fraction.  
Operational usability breakpoint B\_inf:  
first severity with mean infinite-interval fraction ≥ 0.05 for two consecutive severity levels.  
Sensitivity thresholds: 0.01 and 0.10.

Finite mean/median width and finite interval score remain descriptive when infinite intervals occur. A method with non-zero infinite-interval frequency must never be declared superior solely because its finite-only interval score is smaller.

19.8 Locked ranking-instability analysis  
Ranking is metric-specific; no new scalar super-score will be created.

Primary ordering diagnostic:  
one-sided coverage deficit, lower is better.

Secondary ordering diagnostics:  
absolute coverage gap;  
infinite-interval fraction;  
finite interval score only in conditions where all compared methods have zero infinite-interval frequency.

Within each shift family, compare method ordering at each severity against δ=0 using pairwise reversal fraction and Kendall tau with explicit tie handling. Cross-family summaries may aggregate reversal frequencies, but equal numeric severity across families must not be interpreted as equal distributional distance.

19.9 Locked statistical analysis  
Pointwise summaries: mean, SD, Monte Carlo SE and 95% CI over 30 paired repetitions.  
Paired method effects: paired mean difference and 95% CI using identical repetition seeds.  
Curve-level summaries: trapezoidal integrated coverage deficit and integrated usability diagnostics computed per repetition, followed by paired confidence intervals.  
Breakpoint summaries: primary aggregate persistent breakpoint plus replicate-level breakpoint distribution/median where identifiable.  
Hypothesis tests are secondary to effect sizes and confidence intervals. If formal multiple pairwise tests are reported, Holm correction will be used within each declared metric family.

19.10 Locked primary hypotheses  
H1. Standard SCP coverage deficit increases materially under at least some controlled covariate-shift trajectories.  
H2. Correct oracle weighting can recover coverage in shift families with analytic density ratios, but support/information fragility and usability may deteriorate before or while coverage is preserved.  
H3. Estimated weighting may differ materially from oracle weighting even when ESS or held-out domain-discrimination diagnostics appear acceptable; direct weight-fidelity diagnostics are therefore necessary.  
H4. Method ordering is not stable across shift severity/family, and the ordering depends on which validity/usability metric is used.  
H5. Coverage failure, information fragility and usability failure are empirically distinct events and should not be collapsed into a single score.

19.11 Secondary sensitivity plan  
Coverage levels 0.80 and 0.95: reduced subset only, using DGP-L/N-G and selected mean, variance and tail-mixture shifts at δ ∈ {0,1,2}.  
Outcome heavy-tail sensitivity: scaled Student-t(df=3) noise on a reduced DGP/shift subset.  
Base-regressor sensitivity: Random Forest on a reduced subset after core results are frozen; it is not part of the primary factorial core.  
Density-ratio sensitivity C=0.01 remains mandatory throughout the core because it was selected before the final run.

19.12 Reproducibility and anti-tuning rules  
No primary threshold, severity grid, estimator hyperparameter, method identity, sample size, repetition count or hypothesis may be changed after inspecting v1.0 main results unless a documented error invalidates the locked analysis.

Every run must write:  
raw per-repetition results;  
aggregated summaries;  
paired-difference tables;  
breakpoint tables;  
metric-specific rank-reversal tables;  
configuration YAML;  
software/environment manifest;  
seed manifest;  
run completion/checksum manifest.

No reported numeric result may be manually edited.

19.13 Lock decision  
NOVELTY GATE: CONDITIONAL PASS.  
PRE-LOCK PILOT: PASSED.  
DENSITY-RATIO ESTIMATOR SCREEN: PASSED.  
PROTOCOL v1.0: LOCKED.

The next scientific step is implementation of a v1.0 sharded runner and execution of the 30-repetition primary synthetic experiment. Manuscript Results text must not be finalized from v0.x pilot outputs.  
