# P0-6 — Natural Temporal Deployment-Shift Validation

This post-freeze layer adds a **natural chronological deployment split** to the conformal-regression stress-test artifact. It does not apply the engineered exponential tilts used in the controlled public benchmark.

## Protocol

- Dataset: UCI Gas Turbine CO and NOx Emission Data Set, DOI `10.24432/C5WC95`.
- Source years: **2011-2013**.
- Target years: **2014** and **2015**, evaluated separately.
- Repetitions: **20 paired repetitions**.
- Per repetition: 12,000 source-train, 1,000 source-calibration, 1,000 source domain-fit, 1,000 unlabeled target, 1,000 labeled target-reference calibration, and 1,000 target-test rows.
- No engineered target tilt is applied.

Practical target-label-free methods are SCP-Ridge, Estimated-WCP-Logit, Estimated-WCP-HGB, KMM-CP-Ridge, and RLCP-Ridge. `Target-Cal-SCP-Reference` deliberately uses labeled target-year calibration outcomes and is **diagnostic only**, not a deployable comparator.

The temporal split may contain conditional/process drift in addition to marginal covariate shift, so P0-6 is not interpreted as an exact covariate-shift validity experiment.

## Main findings

Source-calibrated SCP coverage falls from **0.8557 in 2014** to **0.6391 in 2015**. Logistic WCP and KMM-CP recover part of the loss (2015 coverage 0.8151 and 0.8260), while the labeled-target reference stays near nominal coverage (0.8954 and 0.8999) and widens materially in 2015.

HGB weighting gives high one-sided coverage but severe usability failure: 72.29% of 2014 intervals and 59.72% of 2015 intervals are unbounded, with calibration ESS ratios 0.0359 and 0.0203. RLCP remains finite but changes little relative to SCP in the harsher 2015 deployment year.

## Reproduction

`run_p06_temporal_deployment.py` is portable across the cumulative supplement and a repository checkout. Set `P06_GAS_TURBINE_CSV` to the canonical Gas Turbine NOx CSV. Raw third-party UCI data are not redistributed. The local `kmm_core_p02.py` preserves the audited KMM implementation used by the frozen run.

Compact frozen records are under `results/`; the complete frozen 240-row table and cumulative verifier are archived in the manuscript supplement.
