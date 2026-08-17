# Real-data benchmark

This directory contains the final executed public-data benchmark and its acquisition/validation code.

The filename `configs/real_data_prelock.json` is intentionally retained unchanged because the merged result manifests bind the executed configuration to SHA-256
`b1aeef06011ba4c112737e9622f6a5adc477e87e76d36ebad5b6557871b6805a`.
The scientific design was subsequently locked without changing this executed JSON payload. Renaming or editing the JSON content is unnecessary for reproduction and would complicate provenance comparisons.

Raw UCI input files are excluded. See `../docs/DATASETS.md`.

## Tests

```bash
PYTHONPATH=code python -m pytest -q tests
```

## Directional benchmark

```bash
bash scripts/run_directional.sh
```

## Radial sensitivity

On Windows PowerShell, after the canonical data have been acquired:

```powershell
.\scripts\run_radial_sensitivity.ps1
```
