# P0-7 Computational and Scalability Audit

## Purpose
P0-7 closes the explicit computational/scalability limitation without changing any frozen scientific result from P0-2 through P0-6. It measures the implementation cost of the benchmark mechanisms under controlled synthetic workloads and separates predictor fitting, conformal calibration, ratio/localization fitting, weight evaluation, and interval inference.

## Final execution protocol
- Final timing jobs were executed sequentially; no two timed method batches overlapped.
- NumPy/SciPy OpenBLAS and scikit-learn OpenMP pools were verified at one thread with `threadpoolctl`.
- Python import time, synthetic-data generation, and a common numerical warmup are excluded from method timings.
- Reference condition: mean shift severity 1.0, p=20, n_train=n_cal=n_unlabeled=n_test=1000, five repetitions.
- Dimension axis: p={5,20,50,100}, three repetitions per point.
- Calibration/unlabeled axis: n_cal=n_unlabeled={250,500,1000,1500}, p=20, three repetitions per point.
- Test axis: n_test={250,1000,2500,5000}, p=20 and n_cal=1000, three repetitions per point.
- Methods: SCP-Ridge, CQR-GBR, Oracle-WCP-Ridge, Estimated-WCP-Logistic, HGB-WCP-Ridge, uLSIF-WCP-Ridge, KMM-CP-Ridge, and RLCP-Ridge.
- Incremental peak RSS is sampled every 3 ms. Only the first observation of each isolated method-by-axis subprocess is interpreted as a fresh-process memory reference.

## QA correction history
Two orchestration pilots were rejected before freezing P0-7:
1. A concurrent-process pilot was excluded because CPU contention inflated wall-clock times, most visibly for KMM.
2. A nominally sequential pilot was excluded after `threadpoolctl` showed the container OpenBLAS default was five threads despite environment-variable requests.

The final run uses explicit `threadpool_limits(1)` and was executed sequentially. Neither rejected pilot is used in the manuscript, frozen P0-7 result tables, or scaling estimates.

## Reference-condition median cost
| Method | Total (ms) | Ratio/local fit (ms) | Inference (ms) | Fresh peak RSS delta (MB) |
|---|---:|---:|---:|---:|
| SCP-Ridge | 1.723 | 0 | 0.104 | 0.539 |
| Oracle-WCP-Ridge | 2.099 | 0 | 0.262 | 0.910 |
| uLSIF-WCP-Ridge | 32.206 | 27.588 | 0.369 | 5.242 |
| Estimated-WCP-Logistic | 53.634 | 34.338 | 0.331 | 8.156 |
| RLCP-Ridge | 115.670 | 72.642 | 41.713 | 7.207 |
| HGB-WCP-Ridge | 181.340 | 168.907 | 0.472 | 3.934 |
| KMM-CP-Ridge | 255.874 | 253.512 | 0.378 | 24.301 |
| CQR-GBR | 1303.740 | N/A | 2.511 | 1.980 |

## Scaling findings
- Estimated-WCP-Logistic total runtime increases by about 71.8x from p=5 to p=100; its empirical log-log exponent is 1.44. Fresh-process peak RSS is 2.04 MB at p=5 versus 171.06 MB at p=100.
- HGB-WCP total runtime increases about 7.39x from p=5 to p=100; uLSIF-WCP increases about 5.92x. Their p=100 fresh-process RSS deltas are 13.02 MB and 8.38 MB, respectively.
- KMM ratio/localization fitting rises from a median 0.0815 s at n_cal=n_unlabeled=250 to 0.3508 s at 1500 (4.30x; empirical exponent 0.856). Fresh-process peak RSS rises from 3.04 MB to 53.02 MB over the same endpoints.
- RLCP bandwidth selection is approximately flat across the calibration/unlabeled axis because the locked bandwidth rule is source-training-only; its computational growth appears instead in per-test localized inference. RLCP inference rises from 25.6 ms at n_test=250 to 128.7 ms at 5000 (5.03x; empirical exponent 0.546).
- CQR-GBR has the largest reference end-to-end cost because two boosted quantile models dominate predictor fitting. Its inference alone remains small compared with its training cost.

## Interpretation boundary
All exponents are empirical slopes over the stated finite grid, not theoretical complexity claims. Absolute wall-clock times are hardware/software dependent. P0-7 is intended to reveal which benchmark mechanism dominates computation and memory under common workloads, not to establish a universal implementation leaderboard.

## Integrity checks
- 29 isolated method-by-axis batch files.
- 292 total timing records.
- Duplicate method/axis/value/repetition keys: 0.
- All component and total times: finite and nonnegative.
- Maximum KMM projected-gradient residual: 9.741146394028209e-05.
- KMM residual failures above 1e-4: 0.
