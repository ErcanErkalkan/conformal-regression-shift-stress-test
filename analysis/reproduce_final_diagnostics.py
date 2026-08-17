from __future__ import annotations
from pathlib import Path
import itertools
import numpy as np
import pandas as pd
from scipy.stats import rankdata, t

ROOT=Path(__file__).resolve().parents[1]
OUT=Path(__file__).resolve().parent/'reproduced'
OUT.mkdir(exist_ok=True)

def ci_sign(x):
    x=np.asarray(x,float); n=len(x); mu=x.mean()
    if n<2: return 0
    se=x.std(ddof=1)/np.sqrt(n); q=t.ppf(.975,n-1)
    lo,hi=mu-q*se,mu+q*se
    return 1 if lo>0 else (-1 if hi<0 else 0)

def rank_layer(raw, layer, profile_cols, methods, metrics):
    rows=[]
    for metric in metrics:
        total=descr=ci_rev=0; base_dist=base_total=0
        for prof,g in raw[raw.method.isin(methods)].groupby(profile_cols, dropna=False):
            b=g[g.severity==0]
            if len(b)==0: continue
            # Interval-score baseline comparisons are counted only for profiles
            # that have at least one eligible positive-severity condition.
            if metric=='interval_score_finite':
                has_eligible=False
                for _,eg in g[g.severity>0].groupby('severity'):
                    chk=eg.groupby('method').infinite_interval_fraction.mean()
                    if len(chk)==len(methods) and not (chk>0).any():
                        has_eligible=True; break
                if not has_eligible:
                    continue
            pairs=list(itertools.combinations(methods,2))
            bsign={}
            for a,c in pairs:
                ma=b[b.method==a][['rep',metric]].rename(columns={metric:'a'})
                mb=b[b.method==c][['rep',metric]].rename(columns={metric:'b'})
                z=ma.merge(mb,on='rep'); d=z.a-z.b
                bsign[(a,c)]=(np.sign(d.mean()),ci_sign(d))
                base_total+=1
                if bsign[(a,c)][1]!=0: base_dist+=1
            for sev,gs in g[g.severity>0].groupby('severity'):
                if metric=='interval_score_finite':
                    chk=gs[gs.method.isin(methods)].groupby('method').infinite_interval_fraction.mean()
                    if len(chk)<len(methods) or (chk>0).any(): continue
                total+=1; any_d=False; any_ci=False
                for a,c in pairs:
                    ma=gs[gs.method==a][['rep',metric]].rename(columns={metric:'a'})
                    mb=gs[gs.method==c][['rep',metric]].rename(columns={metric:'b'})
                    z=ma.merge(mb,on='rep'); d=z.a-z.b
                    sm=np.sign(d.mean()); sc=ci_sign(d); bm,bc=bsign[(a,c)]
                    if bm!=0 and sm!=0 and bm!=sm: any_d=True
                    if bc!=0 and sc!=0 and bc!=sc: any_ci=True
                descr += int(any_d); ci_rev += int(any_ci)
        rows.append(dict(layer=layer,metric=metric,
            descriptive_conditions_with_any_reversal=descr,
            descriptive_eligible_conditions=total,
            ci_screened_conditions_with_any_reversal=ci_rev,
            ci_screened_eligible_conditions=total,
            baseline_pair_profile_comparisons_distinguishable_by_95CI=base_dist,
            baseline_pair_profile_comparisons_total=base_total))
    return rows

syn_path=ROOT/'synthetic/results/primary/raw_results_v10.csv'
dir_path=ROOT/'real_data/results/directional/raw_results_real_v03.csv'
rad_path=ROOT/'real_data/results/radial/raw_results_real_v03.csv'
if not syn_path.exists():
    print('Synthetic per-repetition raw table is not tracked in Git. Run the locked synthetic experiment to regenerate synthetic/results/primary/raw_results_v10.csv before full diagnostic recomputation.')
    raise SystemExit(2)
syn=pd.read_csv(syn_path)
dirn=pd.read_csv(dir_path)
rad=pd.read_csv(rad_path)
metrics=['coverage_deficit','coverage_gap','infinite_interval_fraction','interval_score_finite']
rank=[]
rank+=rank_layer(syn,'Synthetic',['dgp','noise','shift_family'],['SCP-Ridge','CQR-GBR','Estimated-WCP-Primary'],metrics)
rank+=rank_layer(dirn,'Real directional',['dataset'],['SCP-Ridge','CQR-GBR','Estimated-WCP-Primary','Oracle-WCP-Ridge'],metrics)
rank+=rank_layer(rad,'Real radial',['dataset'],['SCP-Ridge','CQR-GBR','Estimated-WCP-Primary','Oracle-WCP-Ridge'],metrics)
pd.DataFrame(rank).to_csv(OUT/'rank_robustness_summary.csv',index=False)

# Direct weight fidelity vs construction oracle, condition means.
def fidelity(raw):
    p=raw[raw.method=='Estimated-WCP-Primary']
    o=raw[raw.method=='Oracle-WCP-Ridge'][['dataset','rep','shift_mode','severity','coverage']].rename(columns={'coverage':'oracle_coverage'})
    m=p.merge(o,on=['dataset','rep','shift_mode','severity'])
    m=m[m.severity>0].copy()
    m['abs_coverage_divergence']=(m.coverage-m.oracle_coverage).abs()
    return m.groupby(['dataset','shift_mode','severity'],as_index=False).agg(
        abs_coverage_divergence=('abs_coverage_divergence','mean'),
        log_weight_rmse=('log_weight_rmse','mean'),
        estimated_ess_ratio=('ess_ratio','mean'))
cond=pd.concat([fidelity(dirn),fidelity(rad)],ignore_index=True).sort_values(['dataset','shift_mode','severity'])
cond.to_csv(OUT/'weight_fidelity_condition_means.csv',index=False)

def rho(df,col):
    x=rankdata(np.asarray(df[col],float)); y=rankdata(np.asarray(df.abs_coverage_divergence,float))
    return float(np.corrcoef(x,y)[0,1])
print('Spearman rho(log-weight RMSE)=',rho(cond,'log_weight_rmse'))
print('Spearman rho(estimated ESS)=',rho(cond,'estimated_ess_ratio'))
lodo=[]
for ds in sorted(cond.dataset.unique()):
    z=cond[cond.dataset!=ds]
    lodo.append({'omitted_dataset':ds,'rho_log_weight_rmse':rho(z,'log_weight_rmse'),'rho_estimated_ess':rho(z,'estimated_ess_ratio')})
pd.DataFrame(lodo).to_csv(OUT/'weight_fidelity_leave_one_dataset_out.csv',index=False)

# Dataset-cluster bootstrap; resample whole dataset identities and retain all mode/severity rows.
rng=np.random.default_rng(20260817); datasets=np.array(sorted(cond.dataset.unique()))
vals=[]
for _ in range(10000):
    picks=rng.choice(datasets,size=len(datasets),replace=True)
    parts=[]
    for j,ds in enumerate(picks):
        q=cond[cond.dataset==ds].copy(); q['boot_cluster']=j; parts.append(q)
    b=pd.concat(parts,ignore_index=True)
    rr=rho(b,'log_weight_rmse'); re=rho(b,'estimated_ess_ratio')
    vals.append((rr,re,abs(rr)-abs(re)))
a=np.array(vals)
qs=np.quantile(a,[.025,.5,.975],axis=0)
out=pd.DataFrame([
 {'quantity':'rho_log_weight_rmse','q025':qs[0,0],'median':qs[1,0],'q975':qs[2,0]},
 {'quantity':'rho_estimated_ess','q025':qs[0,1],'median':qs[1,1],'q975':qs[2,1]},
 {'quantity':'absolute_rho_difference','q025':qs[0,2],'median':qs[1,2],'q975':qs[2,2]}])
out.to_csv(OUT/'weight_fidelity_cluster_bootstrap.csv',index=False)
