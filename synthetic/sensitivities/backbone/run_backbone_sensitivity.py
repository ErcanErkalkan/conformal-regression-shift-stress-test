from pathlib import Path
import argparse
import sys
import numpy as np
import pandas as pd
from scipy.stats import t
from sklearn.ensemble import GradientBoostingRegressor

PARSER = argparse.ArgumentParser(description='Reproduce the locked backbone sensitivity from frozen primary results.')
PARSER.add_argument('--synthetic-root', type=Path, default=Path(__file__).resolve().parents[2])
PARSER.add_argument('--primary-results', type=Path, default=None)
PARSER.add_argument('--out', type=Path, default=None)
ARGS = PARSER.parse_args()
ROOT = ARGS.synthetic_root.resolve()
sys.path.insert(0, str(ROOT/'src'))
from cpshift.runner_v10 import derived_seed
from cpshift.data_v10 import generate_source_split, generate_target, sample_target_covariates, oracle_density_ratio
from cpshift.conformal import conformal_quantile
from cpshift.metrics import interval_metrics, weight_diagnostics

MASTER=2026081601
ALPHA=0.1
NTRAIN=1000; NCAL=1000; NTEST=2500; P=5
DGPS=['linear','nonlinear']; NOISES=['gaussian','heteroscedastic']
FAMS=['mean','variance','mixture','tail_mixture']; SEVS=[0.0,1.0,2.0]
REPS=30
PRIMARY = (ARGS.primary_results or (ROOT/'results'/'primary')).resolve()
OUT = (ARGS.out or (Path(__file__).resolve().parent/'reproduced')).resolve()
OUT.mkdir(parents=True, exist_ok=True)

class SplitConformalGBR:
    def __init__(self, alpha, random_state):
        self.alpha=alpha
        self.model=GradientBoostingRegressor(loss='squared_error', n_estimators=80, learning_rate=0.1, max_depth=3, random_state=random_state)
        self.scores=None; self.qhat=None
    def fit(self,Xtr,ytr,Xcal,ycal):
        self.model.fit(Xtr,ytr)
        pc=self.model.predict(Xcal)
        self.scores=np.abs(ycal-pc)
        self.qhat=conformal_quantile(self.scores,self.alpha)
        return self
    def predict(self,X):
        p=self.model.predict(X)
        return p-self.qhat,p+self.qhat
    def predict_weighted(self,X,wcal,wtest):
        order=np.argsort(self.scores)
        s=self.scores[order]; w=np.asarray(wcal)[order]
        cw=np.cumsum(w); total=float(cw[-1])
        target=(1-self.alpha)*(total+np.asarray(wtest,float))
        idx=np.searchsorted(cw,target,side='left')
        q=np.full(len(wtest),np.inf)
        fin=idx<len(s); q[fin]=s[idx[fin]]
        p=self.model.predict(X)
        return p-q,p+q

rows=[]
for rep in range(REPS):
  for di,dgp in enumerate(DGPS):
    for ni,noise in enumerate(NOISES):
      source_seed=derived_seed(MASTER,rep,di,ni,100)
      model_seed=derived_seed(MASTER,rep,di,ni,200)
      Xtr,ytr,Xcal,ycal=generate_source_split(np.random.default_rng(source_seed),NTRAIN,NCAL,P,dgp,noise)
      gbr=SplitConformalGBR(ALPHA,model_seed).fit(Xtr,ytr,Xcal,ycal)
      baseline_u_seed=derived_seed(MASTER,rep,di,ni,0,0,301)
      baseline_t_seed=derived_seed(MASTER,rep,di,ni,0,0,302)
      baseline_Xu=sample_target_covariates(np.random.default_rng(baseline_u_seed),1000,P,FAMS[0],0.0)
      baseline_Xt,baseline_yt=generate_target(np.random.default_rng(baseline_t_seed),NTEST,P,FAMS[0],0.0,dgp,noise)
      for fi,fam in enumerate(FAMS):
        # Use original family indices from primary runner: mean=0 variance=1 mixture=2 tail=3, same here.
        for sev in SEVS:
          # original severity indices in locked grid {0,.5,1,1.5,2}
          si={0.0:0,1.0:2,2.0:4}[sev]
          if sev==0:
            Xt,yt=baseline_Xt,baseline_yt
          else:
            t_seed=derived_seed(MASTER,rep,di,ni,fi,si,302)
            Xt,yt=generate_target(np.random.default_rng(t_seed),NTEST,P,fam,sev,dgp,noise)
          base=dict(rep=rep,dgp=dgp,noise=noise,shift_family=fam,severity=sev)
          lo,hi=gbr.predict(Xt)
          met=interval_metrics(yt,lo,hi,ALPHA)
          rows.append({**base,'method':'SCP-GBR',**met,'ess_ratio':1.0})
          wc=oracle_density_ratio(Xcal,fam,sev); wt=oracle_density_ratio(Xt,fam,sev)
          if wc is not None and wt is not None:
            lo,hi=gbr.predict_weighted(Xt,wc,wt)
            met=interval_metrics(yt,lo,hi,ALPHA); wd=weight_diagnostics(wc)
            rows.append({**base,'method':'Oracle-WCP-GBR',**met,**wd})

new=pd.DataFrame(rows)
new.to_csv(OUT/'raw_backbone_v11.csv',index=False)

# Pull paired reference rows from locked primary experiment.
raw0=pd.read_csv(PRIMARY/'raw_results_v10.csv')
ref=raw0[(raw0.shift_family.isin(FAMS)) & (raw0.severity.isin(SEVS)) & (raw0.method.isin(['SCP-Ridge','CQR-GBR','Oracle-WCP-Ridge']))].copy()
keep=['rep','dgp','noise','shift_family','severity','method','coverage','coverage_gap','coverage_deficit','mean_width_finite','interval_score_finite','infinite_interval_fraction','ess_ratio']
ref=ref[keep]
allr=pd.concat([ref,new[keep]],ignore_index=True)
allr.to_csv(OUT/'raw_with_references_v11.csv',index=False)

# Summary / t CI
grp=['dgp','noise','shift_family','method','severity']
s=allr.groupby(grp,as_index=False).agg(coverage_mean=('coverage','mean'),coverage_sd=('coverage','std'),coverage_deficit_mean=('coverage_deficit','mean'),coverage_gap_mean=('coverage_gap','mean'),infinite_fraction_mean=('infinite_interval_fraction','mean'),ess_ratio_mean=('ess_ratio','mean'),interval_score_mean=('interval_score_finite','mean'))
crit=float(t.ppf(.975,REPS-1)); s['coverage_se']=s.coverage_sd/np.sqrt(REPS); s['coverage_ci95_low']=np.clip(s.coverage_mean-crit*s.coverage_se,0,1); s['coverage_ci95_high']=np.clip(s.coverage_mean+crit*s.coverage_se,0,1)
s.to_csv(OUT/'summary_backbone_v11.csv',index=False)

# Paired differences for key pairs.
def paired(a,b):
 out=[]
 keys=['dgp','noise','shift_family','severity','rep']
 aa=allr[allr.method==a][keys+['coverage']].rename(columns={'coverage':'a'})
 bb=allr[allr.method==b][keys+['coverage']].rename(columns={'coverage':'b'})
 m=aa.merge(bb,on=keys)
 for key,g in m.groupby(keys[:-1]):
  d=(g.a-g.b).to_numpy(); mu=float(d.mean()); sd=float(d.std(ddof=1)); se=sd/np.sqrt(len(d)); q=float(t.ppf(.975,len(d)-1))
  out.append(dict(zip(keys[:-1],key))|{'comparison':f'{a} - {b}','n':len(d),'mean_diff':mu,'ci95_low':mu-q*se,'ci95_high':mu+q*se})
 return out
pairs=paired('SCP-GBR','SCP-Ridge')+paired('Oracle-WCP-GBR','Oracle-WCP-Ridge')+paired('SCP-GBR','CQR-GBR')
pd.DataFrame(pairs).to_csv(OUT/'paired_coverage_backbone_v11.csv',index=False)

# Reduced-grid persistent Bcov: sev 1 and 2 both below .87.
b=[]
for key,g in s.groupby(['dgp','noise','shift_family','method']):
 gm=g.set_index('severity')
 val=np.nan
 if 1.0 in gm.index and 2.0 in gm.index and gm.loc[1.0,'coverage_mean']<.87 and gm.loc[2.0,'coverage_mean']<.87:
  val=1.0
 b.append(dict(zip(['dgp','noise','shift_family','method'],key))|{'B_cov_reduced':val})
pd.DataFrame(b).to_csv(OUT/'breakpoints_backbone_v11.csv',index=False)

# Integrity and targeted strongest cases.
assert len(new)==2*2*4*3*30*2
assert not new[['coverage','coverage_gap','coverage_deficit','infinite_interval_fraction']].isna().any().any()
print('new rows',len(new),'all rows',len(allr))
print('\nSeverity=2 nonlinear/heteroscedastic:')
print(s[(s.dgp=='nonlinear')&(s.noise=='heteroscedastic')&(s.severity==2)][['shift_family','method','coverage_mean','coverage_ci95_low','coverage_ci95_high','ess_ratio_mean','infinite_fraction_mean']].to_string(index=False))
print('\nBcov counts:')
print(pd.read_csv(OUT/'breakpoints_backbone_v11.csv').groupby('method').B_cov_reduced.apply(lambda x:x.notna().sum()))
