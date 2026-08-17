# Protocol v1.0.1 validation record

Validation performed before any v1.0 main-result run.

- Automated tests: **19/19 passed**.
- Full-factor small-sample smoke: passed end-to-end.
- Baseline/breakpoint semantic guard: breakpoints search only delta > 0; baseline quality is exported separately.
- Shard invariance check: a two-repetition smoke was run once as one job and once as two one-repetition shards. After merge:
  - rows: 484 vs 484;
  - keys: identical;
  - maximum numeric difference: 3.552713678800501e-15 (floating-point serialization level).
- Merge safety:
  - rejects version mismatch;
  - rejects config SHA-256 mismatch;
  - rejects missing/extra repetition IDs;
  - rejects duplicate result keys;
  - rejects unexpected raw-result row count;
  - rejects unexpected seed-manifest row count.
- Locked main config SHA-256: `22bd2bd5054ffa929878f8c5a4dccdbcc7c8abe51c038a7f9624721d5d63123a`.
- Locked main expected rows: 14,520 method-result rows and 3,000 condition-seed rows.

This validation is software/protocol evidence only. Smoke and pre-lock outputs are not manuscript final results.
