from pathlib import Path
import json, hashlib, math
import numpy as np, pandas as pd
from scipy.stats import t
HERE=Path(__file__).resolve().parent
OUT=HERE/'results'; OUT.mkdir(exist_ok=True)
INPUT=HERE/'final_reps'
files=sorted(INPUT.glob('rep*.csv'))
raw=pd.concat([pd.read_csv(f) for f in files],ignore_index=True)
key=['layer','rep','dimension','shift_family','severity','method']
assert len(files)==30
assert len(raw)==30*4*4*3*3, len(raw)
assert raw.duplicated(key).sum()==0
assert set(raw.rep.unique())==set(range(30))
assert ((raw.coverage>=0)&(raw.coverage<=1)).all()
raw.to_csv(OUT/'raw_p05_highdim.csv',index=False)
rows=[]
for k,g in raw.groupby(['rep','dimension','shift_family','method']):
    g=g.sort_values('severity'); x=g.severity.to_numpy(float)
    r=dict(zip(['rep','dimension','shift_family','method'],k))
    for col,name in [('coverage_deficit','A_cov'),('coverage_gap','A_gap'),('infinite_interval_fraction','A_inf')]:
        r[name]=float(np.trapezoid(g[col].to_numpy(float),x))
    r['A_info']=float(np.trapezoid(1-g.ess_ratio.to_numpy(float),x))
    r['A_wRMSE']=float(np.trapezoid(g.log_weight_rmse.to_numpy(float),x)) if g.log_weight_rmse.notna().all() else np.nan
    rows.append(r)
areas=pd.DataFrame(rows); areas.to_csv(OUT/'path_areas_p05_highdim.csv',index=False)
summary=areas.groupby(['dimension','shift_family','method'],as_index=False).agg(A_cov=('A_cov','mean'),A_gap=('A_gap','mean'),A_inf=('A_inf','mean'),A_info=('A_info','mean'),A_wRMSE=('A_wRMSE','mean'))
summary.to_csv(OUT/'area_summary_p05_highdim.csv',index=False)
endpoint=raw[raw.severity==2.0].groupby(['dimension','shift_family','method'],as_index=False).agg(coverage=('coverage','mean'),coverage_gap=('coverage_gap','mean'),inf_frac=('infinite_interval_fraction','mean'),ess_ratio=('ess_ratio','mean'),log_weight_rmse=('log_weight_rmse','mean'),shift_auc=('shift_classifier_auc','mean'),ratio_fit_seconds=('ratio_fit_seconds','mean'),ratio_n_iter=('ratio_n_iter','mean'))
endpoint.to_csv(OUT/'endpoint_summary_p05_highdim.csv',index=False)
def ci(d):
    d=np.asarray(d,float); d=d[np.isfinite(d)]; n=len(d)
    if n<2: return n,np.nan,np.nan,np.nan
    m=float(d.mean()); se=float(d.std(ddof=1)/math.sqrt(n)); c=float(t.ppf(.975,n-1)); return n,m,m-c*se,m+c*se
contr=[]
for (fam,method),g in areas.groupby(['shift_family','method']):
    piv=g.pivot(index='rep',columns='dimension',values=['A_cov','A_gap','A_inf','A_info','A_wRMSE'])
    for metric in ['A_cov','A_gap','A_inf','A_info','A_wRMSE']:
        P=piv[metric]
        if 5 in P and 100 in P:
            n,m,lo,hi=ci((P[100]-P[5]).dropna())
            contr.append({'shift_family':fam,'method':method,'metric':metric,'contrast':'p100-p5','n':n,'mean_difference':m,'ci95_low':lo,'ci95_high':hi})
contr=pd.DataFrame(contr); contr.to_csv(OUT/'dimension_contrasts_p05.csv',index=False)
est=raw[raw.method=='Estimated-WCP-Primary']
comp=est.groupby('dimension',as_index=False).agg(poly_feature_count=('poly_feature_count','first'),fit_seconds_mean=('ratio_fit_seconds','mean'),fit_seconds_median=('ratio_fit_seconds','median'),n_iter_mean=('ratio_n_iter','mean'),convergence_rate=('ratio_converged','mean'),auc_mean=('shift_classifier_auc','mean'),ess_ratio_mean=('ess_ratio','mean'),weight_rmse_mean=('log_weight_rmse','mean'))
comp.to_csv(OUT/'estimator_scaling_p05.csv',index=False)
headline=[]
for fam in sorted(raw.shift_family.unique()):
    for method in ['SCP-Ridge','Oracle-WCP-Ridge','Estimated-WCP-Primary']:
        a=summary[(summary.shift_family==fam)&(summary.method==method)].set_index('dimension')
        e=endpoint[(endpoint.shift_family==fam)&(endpoint.method==method)].set_index('dimension')
        headline.append({'shift_family':fam,'method':method,'A_cov_p5':float(a.loc[5,'A_cov']),'A_cov_p100':float(a.loc[100,'A_cov']),'A_info_p5':float(a.loc[5,'A_info']),'A_info_p100':float(a.loc[100,'A_info']),'coverage_delta2_p5':float(e.loc[5,'coverage']),'coverage_delta2_p100':float(e.loc[100,'coverage']),'ess_delta2_p5':float(e.loc[5,'ess_ratio']),'ess_delta2_p100':float(e.loc[100,'ess_ratio']),'wRMSE_delta2_p5':float(e.loc[5,'log_weight_rmse']) if np.isfinite(e.loc[5,'log_weight_rmse']) else np.nan,'wRMSE_delta2_p100':float(e.loc[100,'log_weight_rmse']) if np.isfinite(e.loc[100,'log_weight_rmse']) else np.nan})
pd.DataFrame(headline).to_csv(OUT/'headline_p05.csv',index=False)
qa={'version':'P0-5-v1','design':'nested nuisance-dimension isolation','repetitions':30,'dimensions':[5,20,50,100],'families':['mean','variance','mixture','tail_mixture'],'severities':[0.0,1.0,2.0],'dgp':'linear','noise':'gaussian','n_train':1000,'n_cal':1000,'n_test':2500,'n_target_unlabeled':1000,'rows':len(raw),'duplicates':int(raw.duplicated(key).sum()),'coverage_outside_0_1':int(((raw.coverage<0)|(raw.coverage>1)).sum()),'estimated_nonconverged':int((~est.ratio_converged.astype(bool)).sum())}
(OUT/'qa_p05.json').write_text(json.dumps(qa,indent=2))
checks=[]
for p in sorted(OUT.iterdir()):
    if p.is_file() and p.name!='checksums_p05.json': checks.append({'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size})
(OUT/'checksums_p05.json').write_text(json.dumps(checks,indent=2))
print('QA',json.dumps(qa,indent=2))
print('\nEST SCALING\n',comp.to_string(index=False))
print('\nHEADLINE\n',pd.DataFrame(headline).to_string(index=False))
print('\nP100-P5 A_COV CONTRASTS\n',contr[contr.metric=='A_cov'].to_string(index=False))
