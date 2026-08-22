# P0-7 — Computational and Scalability Audit

P0-7 adds a controlled computational audit without changing any frozen statistical result from P0-2 through P0-6.

## Frozen protocol

- Eight pipelines: SCP-Ridge, CQR-GBR, Oracle-WCP-Ridge, Estimated-WCP-Logistic, HGB-WCP-Ridge, uLSIF-WCP-Ridge, KMM-CP-Ridge, RLCP-Ridge.
- Final timing jobs are sequential; timed method batches never overlap.
- NumPy/SciPy OpenBLAS and scikit-learn OpenMP pools are verified at one thread with `threadpoolctl`.
- Python import time, synthetic-data generation, and a common numerical warmup are excluded.
- Reference workload: `p=20`, `n_train=n_cal=n_unlabeled=n_test=1000`, mean-shift severity 1.0, five repetitions.
- Scaling axes: `p={5,20,50,100}`, `n_cal=n_unlabeled={250,500,1000,1500}`, and `n_test={250,1000,2500,5000}`, with three repetitions per point.
- Component times are separated into predictor fitting, conformal calibration, ratio/localization fitting, weight evaluation, and interval inference.
- Fresh-process incremental peak RSS is recorded separately from retained-process timing measurements.

## Main findings

At the reference workload, median end-to-end cost ranges from about 1.72 ms for SCP-Ridge and 2.10 ms for Oracle-WCP-Ridge to 1.30 s for CQR-GBR. Estimated-WCP-Logistic costs about 53.6 ms, RLCP about 115.7 ms, HGB-WCP about 181.3 ms, and KMM-CP about 255.9 ms.

Estimated-WCP-Logistic shows the strongest dimension sensitivity: total runtime grows about 71.8x from `p=5` to `p=100`, with empirical log-log exponent 1.44 and fresh-process peak-RSS delta about 171 MB at `p=100`. KMM grows mainly with calibration/unlabeled sample size; RLCP grows mainly in per-test localized inference.

The audit therefore treats computational cost as a separate diagnostic coordinate: low runtime does not imply reliable shift correction, and statistically valid-looking coverage can still be computationally or operationally unusable.

Compact frozen results are versioned in `results/`. The complete 292-row runtime table, portable P0-7 runner/batch/analyzer, cumulative hashes, and verifier are archived in the manuscript reproducibility supplement `Reproducibility_Supplement_P0_7.zip`.
