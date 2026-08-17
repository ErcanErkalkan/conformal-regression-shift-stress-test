Protocol Amendment v1.0.1 — Baseline / Breakpoint Clarification

Reason for amendment  
The first post-lock v1.0 smoke validation exposed a semantic edge case: with deliberately small smoke samples, a method can under-cover at δ=0. If the breakpoint search includes δ=0, the software can report B\_cov=0, incorrectly labeling a baseline calibration problem as a shift-induced failure breakpoint.

Classification of change  
Definition/implementation clarification discovered during pre-main-run software validation. This amendment does NOT change the scientific thresholds, methods, sample sizes, severity grid, estimators, hypotheses or repetition count.

Amended rule  
1\. All shift-induced breakpoint searches begin at strictly positive severity (δ\>0).  
2\. δ=0 is the common baseline anchor and is audited separately.  
3\. A δ=0 coverage problem is recorded as baseline\_undercoverage, not B\_cov=0.  
4\. A δ=0 inferential coverage problem is recorded as baseline\_undercoverage\_CI.  
5\. A δ=0 ESS problem is recorded as baseline\_info\_fragile.  
6\. A δ=0 infinite-interval problem is recorded as baseline\_usability\_issue.

Unchanged locked thresholds  
Nominal coverage \= 0.90.  
Coverage lower acceptable bound \= 0.87.  
Coverage persistence \= 2 consecutive positive-severity points.  
Information-fragility threshold \= ESS/n\_cal ≤ 0.20, persistence 2\.  
Usability threshold \= infinite-interval fraction ≥ 0.05, persistence 2\.

Inferential breakpoint clarification  
To establish persistent undercoverage inferentially, the UPPER 95% confidence bound for mean coverage must fall below 0.87. The lower confidence bound is not the correct criterion for concluding that the mean coverage is below the acceptable region.

Software validation after amendment  
• Automated tests: 19/19 passed.  
• Full-factor small-sample smoke: passed.  
• Shard invariance: two 1-repetition shards merged to the same 484 result rows as one 2-repetition run; keys were identical and maximum numeric difference was 3.552713678800501e-15.  
• Merge rejects version mismatch, config-hash mismatch, missing/extra repetitions, duplicate keys, wrong raw-result row count and wrong seed-manifest row count.

Locked main-run integrity values  
Protocol code version: 1.0.1-locked.  
Locked config SHA-256: 22bd2bd5054ffa929878f8c5a4dccdbcc7c8abe51c038a7f9624721d5d63123a.  
Expected main raw method-result rows: 14,520.  
Expected main condition-seed rows: 3,000.

Decision  
AMENDMENT ACCEPTED BEFORE MAIN v1.0 RESULTS.  
The design remains locked. This amendment prevents baseline calibration failures from being mislabeled as shift-induced breakpoints and strengthens reproducibility without outcome-driven tuning.  
