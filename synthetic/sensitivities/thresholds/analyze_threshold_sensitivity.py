from pathlib import Path
import argparse
import sys
import pandas as pd
import numpy as np
PARSER=argparse.ArgumentParser(description='Recompute operational-threshold sensitivity from frozen primary summaries.')
PARSER.add_argument('--synthetic-root', type=Path, default=Path(__file__).resolve().parents[2])
PARSER.add_argument('--primary-results', type=Path, default=None)
PARSER.add_argument('--out', type=Path, default=None)
ARGS=PARSER.parse_args()
ROOT=ARGS.synthetic_root.resolve()
sys.path.insert(0,str(ROOT/'src'))
from cpshift.metrics_v10 import persistent_threshold_breakpoint

base=(ARGS.primary_results or (ROOT/'results'/'primary')).resolve()
out=(ARGS.out or (Path(__file__).resolve().parent/'reproduced')).resolve()
out.mkdir(parents=True,exist_ok=True)
s=pd.read_csv(base/'summary_v10.csv')
gcols=['dgp','noise','shift_family','method']
shifted=s[s.severity>0].copy()
rows=[]
for tau in [0.02,0.03,0.05]:
 for persist in [1,2]:
  lower=.90-tau
  b=persistent_threshold_breakpoint(shifted,gcols,'coverage_mean',lower,'lt',persist,'bp')
  for method,g in b.groupby('method'):
   rows.append({'axis':'coverage','threshold':tau,'persistence':persist,'method':method,'profiles':len(g),'breakpoints':int(g.bp.notna().sum())})
for th in [0.10,0.20,0.30]:
 b=persistent_threshold_breakpoint(shifted,gcols,'ess_ratio_mean',th,'le',2,'bp')
 for method,g in b.groupby('method'):
  rows.append({'axis':'information_ess_ratio','threshold':th,'persistence':2,'method':method,'profiles':len(g),'breakpoints':int(g.bp.notna().sum())})
for th in [0.01,0.05,0.10]:
 b=persistent_threshold_breakpoint(shifted,gcols,'infinite_fraction_mean',th,'ge',2,'bp')
 for method,g in b.groupby('method'):
  rows.append({'axis':'usability_infinite_fraction','threshold':th,'persistence':2,'method':method,'profiles':len(g),'breakpoints':int(g.bp.notna().sum())})
df=pd.DataFrame(rows)
df.to_csv(out/'threshold_sensitivity_counts.csv',index=False)

# three-axis overlap for every threshold triplet at persistence=2
combo=[]
for tau in [0.02,0.03,0.05]:
 bc=persistent_threshold_breakpoint(shifted,gcols,'coverage_mean',.90-tau,'lt',2,'Bcov')
 for ei in [0.10,0.20,0.30]:
  bi=persistent_threshold_breakpoint(shifted,gcols,'ess_ratio_mean',ei,'le',2,'Binfo')
  for ui in [0.01,0.05,0.10]:
   bu=persistent_threshold_breakpoint(shifted,gcols,'infinite_fraction_mean',ui,'ge',2,'Binf')
   m=bc.merge(bi,on=gcols,how='outer').merge(bu,on=gcols,how='outer')
   flags=m[['Bcov','Binfo','Binf']].notna().sum(axis=1)
   combo.append({'coverage_tau':tau,'info_threshold':ei,'usability_threshold':ui,'profiles':len(m),'none':int((flags==0).sum()),'exactly_one':int((flags==1).sum()),'multiple':int((flags>=2).sum()),'coverage_any':int(m.Bcov.notna().sum()),'info_any':int(m.Binfo.notna().sum()),'usability_any':int(m.Binf.notna().sum())})
pd.DataFrame(combo).to_csv(out/'three_axis_overlap_sensitivity.csv',index=False)
print(df.to_string(index=False))
print('\nOverlap combinations with multiple failures range:')
c=pd.DataFrame(combo); print(c[['coverage_tau','info_threshold','usability_threshold','multiple','exactly_one','none']].to_string(index=False))
