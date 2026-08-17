# Reproducibility guide

## Scientific freeze

The primary synthetic protocol, the baseline-breakpoint amendment, the real-data protocol, thresholds, method identities, severity grids, seeds, and density-ratio regularization were frozen before the corresponding final analyses. Versioned compact result summaries, breakpoint tables, and merge/configuration manifests are archival outputs; scripts must not silently rewrite them. Seed manifests, per-repetition raw outputs, paired-difference tables, trajectories, and supplementary sensitivity result tables are intentionally not tracked in Git and are recreated by the locked runners when full recomputation is requested.

## Environment

A fresh Python environment can be created with:

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
python -m pip install -U pip
python -m pip install -r requirements.txt
```

The exact Windows execution package list used for the real-data run is recorded in `real_data/environment_manifest.txt`.

## Verify the Git release

```bash
python verify_release.py
```

Expected primary counts:
- synthetic: 14,520 method-result rows and 3,000 condition-seed rows;
- real directional: 2,500 method-result rows and 500 seed rows;
- real radial: 600 method-result rows and 120 seed rows.

The real-data merged config hash must be `b1aeef06011ba4c112737e9622f6a5adc477e87e76d36ebad5b6557871b6805a`.

## Synthetic tests

```bash
cd synthetic
PYTHONPATH=src python -m pytest -q tests/test_v10.py
```

Full locked rerun:

```bash
cd synthetic
bash scripts/run_locked_v10_sequential.sh
```

## Real-data tests and rerun

```bash
cd real_data
PYTHONPATH=code python -m pytest -q tests
bash scripts/run_directional.sh
```

For the pre-specified radial sensitivity on Windows PowerShell:

```powershell
cd real_data
.\scripts\run_radial_sensitivity.ps1
```

## Post-primary diagnostics

```bash
python analysis/reproduce_final_diagnostics.py
```

The repository includes the final post-primary diagnostic outputs. Full recomputation requires the synthetic per-repetition raw table produced by the locked synthetic runner. When that table is absent, the diagnostic script reports the missing prerequisite without modifying archived outputs. These diagnostics do not alter the locked primary experiments.
