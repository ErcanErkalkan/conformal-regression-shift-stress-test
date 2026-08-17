import json
from pathlib import Path

def test_manifest_has_five_unique_primary_datasets():
    p=Path(__file__).parents[1]/"configs"/"dataset_manifest.json"
    m=json.loads(p.read_text())
    ds=m["datasets"]
    assert len(ds)==5
    assert len({d["uci_id"] for d in ds})==5
    assert all(d["expected_rows"] >= 8000 for d in ds)
    assert all(d["doi"].startswith("10.24432/") for d in ds)


def test_prelock_config_fixed_severity_and_seed():
    p=Path(__file__).parents[1]/"configs"/"real_data_prelock.json"
    c=json.loads(p.read_text())
    assert c["master_seed"]==2026081602
    assert c["directional_tilt_lambda"]==[0.0,0.5,1.0,1.5,2.0]
    assert c["coverage_lower_bound"]==0.87
