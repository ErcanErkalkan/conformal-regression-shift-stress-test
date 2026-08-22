# P0-4 frozen headline results

- Synthetic factorial rows: 17,040 across 30 paired repetitions.
- Public factorial rows: 3,200 across 20 paired repetitions and five UCI datasets.
- Duplicate keys: 0; coverage values outside [0,1]: 0.
- Synthetic analytic profiles: WCP backbone-effect `A_cov` CI includes zero in 16/16 profiles; SCP backbone effect excludes zero in 16/16 (8 positive, 8 negative).
- Public dataset-geometry paths: WCP backbone-effect `A_cov` CI includes zero in 10/10; SCP HGBR-minus-Ridge effect is significantly negative in 7/10 and includes zero in 3/10.
- Persistent undercoverage: synthetic SCP-Ridge 10/16, SCP-GBR 14/16, known-ratio WCP 0/16 for both backbones.
- Persistent undercoverage: public SCP-Ridge 6/10, SCP-HGBR 4/10, known-tilt WCP 0/10 for both backbones.
- Deterministic rep-0 recheck: maximum numeric difference 7.11e-15 synthetic and 2.22e-16 public CCPP.
- Earlier M7 difficult-condition checkpoint reproduced: SCP-Ridge 0.5959867 and SCP-GBR 0.6438400 coverage at severity 2.

The complete frozen raw/pathwise result tables and cumulative verifier are archived in the submission reproducibility supplement rather than duplicated in Git history.
