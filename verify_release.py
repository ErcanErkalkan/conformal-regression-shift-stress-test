from pathlib import Path
import json, hashlib
import pandas as pd
ROOT=Path(__file__).resolve().parent

syn=ROOT/'synthetic/results/primary'
sm=json.loads((syn/'merge_manifest_v10.json').read_text())
assert sm['config_sha256']=='22bd2bd5054ffa929878f8c5a4dccdbcc7c8abe51c038a7f9624721d5d63123a'
assert sm['expected_raw_rows']==14520 and sm['expected_seed_rows']==3000
assert len(pd.read_csv(syn/'summary_v10.csv'))>0
assert len(pd.read_csv(syn/'breakpoints_v10.csv'))>0
print('synthetic locked rows/seeds:',sm['expected_raw_rows'],sm['expected_seed_rows'])

for mode,rows,seeds_n in [('directional',2500,500),('radial',600,120)]:
    p=ROOT/f'real_data/results/{mode}'
    mm=json.loads((p/'merge_manifest_real_v03.json').read_text())
    assert mm['rows']==rows and mm['seed_rows']==seeds_n
    assert mm['config_hash']=='b1aeef06011ba4c112737e9622f6a5adc477e87e76d36ebad5b6557871b6805a'
    assert len(pd.read_csv(p/'summary_real_v03.csv'))>0
    assert len(pd.read_csv(p/'breakpoints_real_v03.csv'))>0
    print(mode,'locked rows/seeds:',rows,seeds_n,'config_hash:',mm['config_hash'])

man=json.loads((ROOT/'real_data/configs/dataset_manifest.json').read_text())
assert next(d for d in man['datasets'] if d['key']=='online_news')['expected_rows']==39644

def norm_bytes(path): return path.read_bytes().replace(b'\r\n',b'\n')
release=json.loads((ROOT/'RELEASE_MANIFEST.json').read_text())
for item in release['files']:
    fp=ROOT/item['path']; assert fp.is_file(),item['path']
    data=norm_bytes(fp)
    assert len(data)==item['normalized_bytes'],item['path']
    assert hashlib.sha256(data).hexdigest()==item['sha256_lf_normalized'],item['path']
print('release manifest files:',len(release['files']))
print('release verification: PASS')
