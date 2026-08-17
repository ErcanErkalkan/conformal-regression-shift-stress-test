from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd

METHODS={"SCP-Ridge","CQR-GBR","Estimated-WCP-Primary","Estimated-WCP-Sensitivity","Oracle-WCP-Ridge"}
DATASETS={"ccpp","appliances","superconductivity","gas_turbine_nox","online_news"}

def check(path: Path, rows: int, seeds: int, datasets: set[str], severities: set[float]):
    raw=pd.read_csv(path/'raw_results_real_v03.csv')
    sm=pd.read_csv(path/'seed_manifest_real_v03.csv')
    manifest=json.loads((path/'merge_manifest_real_v03.json').read_text())
    assert len(raw)==rows==(manifest['rows'])
    assert len(sm)==seeds==(manifest['seed_rows'])
    assert set(raw.method)==METHODS
    assert set(raw.dataset)==datasets
    assert set(map(float,raw.severity.unique()))==severities
    assert raw.duplicated(['dataset','rep','shift_mode','severity','method']).sum()==0
    assert sm.duplicated(['dataset','rep','shift_mode','severity']).sum()==0
    assert raw[['coverage','coverage_gap','coverage_deficit','ess_ratio']].notna().all().all()
    return manifest

ap=argparse.ArgumentParser()
ap.add_argument('--directional', type=Path)
ap.add_argument('--radial', type=Path)
a=ap.parse_args()
if a.directional:
    m=check(a.directional,2500,500,DATASETS,{0.,.5,1.,1.5,2.})
    assert m['config_hash']=='b1aeef06011ba4c112737e9622f6a5adc477e87e76d36ebad5b6557871b6805a'
    print('directional: PASS',m)
if a.radial:
    m=check(a.radial,600,120,{"ccpp","superconductivity"},{0.,1.,2.})
    assert m['config_hash']=='b1aeef06011ba4c112737e9622f6a5adc477e87e76d36ebad5b6557871b6805a'
    print('radial: PASS',m)
