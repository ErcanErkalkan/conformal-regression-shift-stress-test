# P1-3 method-label clarification

Some frozen P0-2/P0-6/P0-7 CSV, JSON, and historical package records use the string `KMM-CP-Ridge` (or `KMM-CP`) for this repository's external kernel-mean-matching comparator.

Inspection of the versioned implementation confirms that those rows correspond to **non-selective classical RBF kernel mean matching followed by a weighted split-conformal absolute-residual cutoff**. The implementation does not contain the support-selection/support-restriction stage of the distinct published method **KMM-CP: Practical Conformal Prediction under Covariate Shift via Selective Kernel Mean Matching** by Laghuvarapu, Deb, and Sun (UAI 2026).

From manuscript P1-3 onward, the evaluated repository comparator is therefore named:

- `KMM-WCP` (method family), or
- `KMM-WCP-Ridge` (when the Ridge backbone is explicit).

Mapping: `historical frozen KMM-CP-Ridge` -> `manuscript KMM-WCP-Ridge`.

This is a terminology/provenance correction only. Frozen numerical outputs, source implementations, timings, confidence intervals, and checksum-covered files are not rewritten. Historical result strings remain readable under the mapping above so prior hashes remain auditable. The selective KMM-CP method is related work and is not claimed to have been reproduced.