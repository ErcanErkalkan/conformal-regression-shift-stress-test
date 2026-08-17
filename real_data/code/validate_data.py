from pathlib import Path
import argparse,json,hashlib,pandas as pd

def sha(p):
    h=hashlib.sha256();
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1<<20),b''):h.update(c)
    return h.hexdigest()

def main():
    a=argparse.ArgumentParser();a.add_argument('--manifest',default='configs/dataset_manifest.json');a.add_argument('--data-dir',default='data/canonical');x=a.parse_args()
    m=json.loads(Path(x.manifest).read_text()); out=[]
    for d in m['datasets']:
        p=Path(x.data_dir)/f"{d['key']}.csv"; df=pd.read_csv(p)
        if len(df)!=d['expected_rows']:raise SystemExit(f"{d['key']}: row mismatch")
        if 'target' not in df:raise SystemExit(f"{d['key']}: target missing")
        if df.isna().any().any():raise SystemExit(f"{d['key']}: missing values")
        out.append({'key':d['key'],'rows':len(df),'predictors':len(df.columns)-1,'sha256':sha(p)})
    Path(x.data_dir,'validation_manifest.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':main()
