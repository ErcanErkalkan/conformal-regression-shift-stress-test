# P0-6 Natural Temporal Deployment-Shift Audit

## Locked design
- Dataset: UCI Gas Turbine CO and NOx Emission Data Set, DOI 10.24432/C5WC95.
- Natural temporal split: 2011-2013 source; 2014 and 2015 evaluated as separate target years.
- No engineered tilt or target resampling weight is imposed.
- Per repetition: 12,000 source-train, 1,000 source-calibration, 1,000 source domain-fit, 1,000 unlabeled target, 1,000 labeled target-calibration reference, and 1,000 target-test rows.
- Practical target-label-free methods: SCP-Ridge, Estimated-WCP-Logit, Estimated-WCP-HGB, KMM-CP-Ridge, RLCP-Ridge.
- `Target-Cal-SCP-Reference` uses 1,000 labeled target calibration outcomes only as a non-deployable diagnostic reference.
- Natural temporal data may contain conditional/process drift in addition to covariate shift; P0-6 is therefore not used as an exact WCP validity experiment.

## QA
- rows: 240
- repetitions: 20
- target_years: [2014, 2015]
- methods: ['Estimated-WCP-HGB', 'Estimated-WCP-Logit', 'KMM-CP-Ridge', 'RLCP-Ridge', 'SCP-Ridge', 'Target-Cal-SCP-Reference']
- duplicate_keys: 0
- coverage_outside_0_1: 0
- kmm_solver_rows: 40
- kmm_pg_over_1e4: 0
- canonical_sha256: 811de4b24d263079000733e700d556ab8c3cdc9e8164d50a45e421a428e8cd17
- year_counts: {'2011': 7411, '2012': 7628, '2013': 7152, '2014': 7158, '2015': 7384}
- rep-0 determinism max absolute numeric diff: 8.882e-16

## Main results
### Target year 2014
- Estimated-WCP-HGB: coverage=0.9832, gap=0.0832, finite-width=4.4556, infinite=0.7229, ESS-ratio=0.0359.
- Estimated-WCP-Logit: coverage=0.8825, gap=0.0263, finite-width=2.3914, infinite=0.0072, ESS-ratio=0.6463.
- KMM-CP-Ridge: coverage=0.8778, gap=0.0272, finite-width=2.3432, infinite=0.0000, ESS-ratio=0.4989.
- RLCP-Ridge: coverage=0.8486, gap=0.0513, finite-width=2.1767, infinite=0.0001, ESS-ratio=NA.
- SCP-Ridge: coverage=0.8557, gap=0.0444, finite-width=2.1883, infinite=0.0000, ESS-ratio=1.0000.
- Target-Cal-SCP-Reference: coverage=0.8954, gap=0.0123, finite-width=2.4751, infinite=0.0000, ESS-ratio=1.0000.
- descriptive shift diagnostics: MMD^2=0.01694; standardized source-Ridge target RMSE=0.7874.
- held-out domain AUC: logistic=0.9944, HGB=0.9954.

### Target year 2015
- Estimated-WCP-HGB: coverage=0.9769, gap=0.0769, finite-width=4.7818, infinite=0.5972, ESS-ratio=0.0203.
- Estimated-WCP-Logit: coverage=0.8151, gap=0.0868, finite-width=2.6676, infinite=0.0911, ESS-ratio=0.3808.
- KMM-CP-Ridge: coverage=0.8260, gap=0.0845, finite-width=2.8409, infinite=0.0000, ESS-ratio=0.1673.
- RLCP-Ridge: coverage=0.6484, gap=0.2515, finite-width=2.2233, infinite=0.0003, ESS-ratio=NA.
- SCP-Ridge: coverage=0.6391, gap=0.2609, finite-width=2.1883, infinite=0.0000, ESS-ratio=1.0000.
- Target-Cal-SCP-Reference: coverage=0.8999, gap=0.0101, finite-width=3.1698, infinite=0.0000, ESS-ratio=1.0000.
- descriptive shift diagnostics: MMD^2=0.04466; standardized source-Ridge target RMSE=1.0708.
- held-out domain AUC: logistic=0.9848, HGB=0.9937.

## Paired interpretation
- 2014 Estimated-WCP-Logit minus SCP coverage-deficit: -0.0225 [-0.0267,-0.0182].
- 2014 KMM-CP-Ridge minus SCP coverage-deficit: -0.0197 [-0.0300,-0.0094].
- 2014 RLCP-Ridge minus SCP coverage-deficit: 0.0070 [0.0027,0.0113].
- 2014 Target-Cal-SCP-Reference minus SCP coverage-deficit: -0.0359 [-0.0428,-0.0290].
- 2014 Estimated-WCP-HGB minus SCP coverage-deficit: -0.0444 [-0.0526,-0.0361].
- 2015 Estimated-WCP-Logit minus SCP coverage-deficit: -0.1750 [-0.1916,-0.1584].
- 2015 KMM-CP-Ridge minus SCP coverage-deficit: -0.1816 [-0.2104,-0.1529].
- 2015 RLCP-Ridge minus SCP coverage-deficit: -0.0094 [-0.0157,-0.0030].
- 2015 Target-Cal-SCP-Reference minus SCP coverage-deficit: -0.2558 [-0.2773,-0.2343].
- 2015 Estimated-WCP-HGB minus SCP coverage-deficit: -0.2609 [-0.2807,-0.2411].
- HGB WCP has zero one-sided deficit in both years because it strongly overcovers; this is not treated as operational superiority because 72.29% (2014) and 59.72% (2015) of intervals are infinite.
- 2015-minus-2014 coverage-deficit for SCP-Ridge: 0.2165 [0.2010,0.2321].
- 2015-minus-2014 coverage-deficit for Estimated-WCP-Logit: 0.0640 [0.0444,0.0836].
- 2015-minus-2014 coverage-deficit for KMM-CP-Ridge: 0.0546 [0.0281,0.0811].
- 2015-minus-2014 coverage-deficit for RLCP-Ridge: 0.2002 [0.1832,0.2172].
- 2015-minus-2014 coverage-deficit for Target-Cal-SCP-Reference: -0.0034 [-0.0096,0.0029].

## Scientific conclusion
The natural deployment shift is substantially harsher in 2015 than 2014. Logistic WCP and KMM recover part of the source-calibration failure but do not approach the labeled-target calibration reference. The latter remains near nominal coverage in both years and widens materially in 2015, consistent with temporal residual/process drift that pure covariate reweighting cannot fully repair. HGB weighting demonstrates the benchmark's usability warning: excellent one-sided coverage can be purchased by extreme weight concentration and a majority of unbounded intervals.
