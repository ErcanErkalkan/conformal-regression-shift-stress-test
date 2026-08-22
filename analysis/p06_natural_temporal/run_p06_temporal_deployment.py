from __future__ import annotations
import argparse, hashlib, json, math, os, sys, time
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
from scipy.stats import t
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score, mean_squared_error
from sklearn.preprocessing import StandardScaler

HERE=Path(__file__).resolve().parent
# Portable source discovery: extracted cumulative supplement first, repository checkout second.
SUPP_ROOT=HERE.parent
REPO_ROOT=HERE.parents[1] if len(HERE.parents)>1 else HERE.parent
real_candidates=[
    SUPP_ROOT/'p03_density_estimator_expansion'/'source'/'real',
    REPO_ROOT/'real_data'/'code',
]
REAL=next((p for p in real_candidates if p.exists()), Path(os.environ.get('P06_REAL_CODE','')))
if not REAL or not REAL.exists():
    raise FileNotFoundError('Cannot locate real-data core code; set P06_REAL_CODE.')
DATA=Path(os.environ.get('P06_GAS_TURBINE_CSV', str(HERE/'data'/'gas_turbine_nox.csv')))
OUT=Path(os.environ.get('P06_OUT', str(HERE/'results'))); OUT.mkdir(parents=True,exist_ok=True)
ALPHA=.10
MASTER=2026082206
REPS=20
N_TRAIN=12000
N_CAL=1000
N_DENS=1000
N_TARGET_UNLAB=1000
N_TARGET_CAL=1000
N_TEST=1000
RLCP_TARGET_ESS=200.0
# UCI original yearly files, excluding header rows. Sum = 36,733.
YEAR_COUNTS={2011:7411,2012:7628,2013:7152,2014:7158,2015:7384}
HGB_PARAMS=dict(max_iter=100,learning_rate=0.08,max_leaf_nodes=15,min_samples_leaf=20,
                l2_regularization=1.0,early_stopping=True,validation_fraction=0.15,
                n_iter_no_change=8,tol=1e-5)

sys.path.insert(0,str(REAL))
from conformal_core import OracleWeightedSplitConformalRidge, conformal_quantile
from density_ratio import fit_density_ratio
from metrics_core import interval_metrics, weight_diagnostics, rbf_mmd2
sys.path.insert(0,str(HERE))
import kmm_core_p02 as kmm


def sha256(p:Path):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1<<20),b''): h.update(c)
    return h.hexdigest()

def dseed(*parts):
    mask=(1<<64)-1; x=int(MASTER)&mask
    for p in parts:
        x ^= (int(p)+0x9E3779B97F4A7C15)&mask
        x = (x*0xBF58476D1CE4E5B9)&mask
        x ^= x >> 27
    return int(x % (2**32-1))

class ClassifierOddsRatio:
    def __init__(self,model,source_mean,clip=1e-5): self.model=model; self.source_mean=float(source_mean); self.clip=float(clip)
    def probabilities(self,X): return self.model.predict_proba(np.asarray(X,float))[:,1]
    def ratio(self,X):
        p=np.clip(self.probabilities(X),self.clip,1-self.clip); r=p/(1-p)
        return r/max(self.source_mean,1e-12)

def fit_hgb_ratio(Xs,Xt,seed):
    Xs=np.asarray(Xs,float); Xt=np.asarray(Xt,float)
    X=np.vstack([Xs,Xt]); y=np.r_[np.zeros(len(Xs),int),np.ones(len(Xt),int)]
    m=HistGradientBoostingClassifier(random_state=int(seed),**HGB_PARAMS).fit(X,y)
    ps=np.clip(m.predict_proba(Xs)[:,1],1e-5,1-1e-5); sm=float(np.mean(ps/(1-ps)))
    return ClassifierOddsRatio(m,sm)

def external_interval_metrics(y,pred,q):
    y=np.asarray(y,float); pred=np.asarray(pred,float); q=np.asarray(q,float)
    pos=np.isposinf(q); neg=np.isneginf(q); fin=np.isfinite(q)
    cov=np.zeros(len(y),bool); cov[pos]=True; cov[fin]=np.abs(y[fin]-pred[fin])<=q[fin]
    if fin.any():
        w=2*q[fin]; lo=pred[fin]-q[fin]; hi=pred[fin]+q[fin]; yf=y[fin]; s=w.copy()
        b=yf<lo; a=yf>hi; s[b]+=(2/ALPHA)*(lo[b]-yf[b]); s[a]+=(2/ALPHA)*(yf[a]-hi[a])
        mw=float(w.mean()); med=float(np.median(w)); score=float(s.mean())
    else: mw=med=score=float('inf')
    coverage=float(cov.mean())
    return {'coverage':coverage,'coverage_gap':abs(coverage-(1-ALPHA)),
            'coverage_deficit':max(0,(1-ALPHA)-coverage),'mean_width_finite':mw,
            'median_width_finite':med,'interval_score_finite':score,
            'infinite_interval_fraction':float(pos.mean()),'empty_interval_fraction':float(neg.mean())}

def _ess(w):
    w=np.asarray(w,float); sw=w.sum(); ss=np.dot(w,w); return sw*sw/ss if ss>0 else 0.

def rlcp_select_h(Xtrain,seed,anchors=64):
    X=np.asarray(Xtrain,float); n,d=X.shape; rng=np.random.default_rng(seed)
    ids=rng.choice(n,size=min(anchors,n),replace=False); A=X[ids]; Znoise=rng.normal(size=(len(A),d))
    js=np.linspace(0,n-1,min(400,n),dtype=int); S=X[js]; target=min(RLCP_TARGET_ESS,.8*len(S))
    def avg(h):
        vals=[]
        for z in A+h*Znoise:
            d2=np.sum((S-z)**2,axis=1); lw=-.5*d2/(h*h); lw-=lw.max(); vals.append(_ess(np.exp(lw)))
        return float(np.median(vals))
    lo,hi=.05,1.
    while avg(hi)<target and hi<64: hi*=1.8
    for _ in range(20):
        mid=(lo+hi)/2
        if avg(mid)<target: lo=mid
        else: hi=mid
    h=(lo+hi)/2
    return h,{'target_ess':target,'selection_median_ess':avg(h),'anchors':len(A),'selection_source_n':len(S)}

def rlcp_thresholds(Xcal,scores,Xtest,h,seed,chunk=96):
    Xcal=np.asarray(Xcal,float); Xtest=np.asarray(Xtest,float); scores=np.asarray(scores,float)
    order=np.argsort(scores); s=scores[order]; C=Xcal[order]; rng=np.random.default_rng(seed); q=np.empty(len(Xtest)); essacc=[]
    for i in range(0,len(Xtest),chunk):
        j=min(len(Xtest),i+chunk); X=Xtest[i:j]; eps=rng.normal(size=X.shape); Z=X+h*eps; U=rng.uniform(size=j-i)
        d2=cdist(Z,C,'sqeuclidean'); logW=-.5*d2/(h*h); logwt=-.5*(eps*eps).sum(axis=1); scale=np.maximum(logW.max(axis=1),logwt)
        W=np.exp(logW-scale[:,None]); wt=np.exp(logwt-scale); total=W.sum(axis=1)+wt; tail=np.cumsum(W[:,::-1],axis=1)[:,::-1]; T=ALPHA*total-U*wt
        inf=T<0; cond=tail>T[:,None]; count=cond.sum(axis=1); idx=count-1; qq=np.full(j-i,-np.inf); fin=(~inf)&(count>0); qq[inf]=np.inf; qq[fin]=s[idx[fin]]; q[i:j]=qq
        Wd=np.exp(logW-logW.max(axis=1)[:,None]); sw=Wd.sum(axis=1); ss=(Wd*Wd).sum(axis=1); essacc.extend(np.divide(sw*sw,ss,out=np.zeros_like(sw),where=ss>0).tolist())
    return q,{'rlcp_local_ess_mean':float(np.mean(essacc)),'rlcp_local_ess_median':float(np.median(essacc))}

def add_year(df):
    if len(df)!=sum(YEAR_COUNTS.values()): raise ValueError('row count does not match UCI 2011-2015 total')
    years=np.empty(len(df),int); a=0
    for year,n in YEAR_COUNTS.items(): years[a:a+n]=year; a+=n
    out=df.copy(); out.insert(0,'year',years); return out

def sample_disjoint(rng,n,sizes):
    idx=rng.permutation(n); out=[]; a=0
    for sz in sizes: out.append(idx[a:a+sz]); a+=sz
    return out

def target_cal_interval(model,Xcal,ycal,Xtest):
    scores=np.abs(np.asarray(ycal)-model.model.predict(Xcal)); q=conformal_quantile(scores,ALPHA); p=model.model.predict(Xtest); return p-q,p+q

def run(rep_start=0,rep_end=REPS):
    df=add_year(pd.read_csv(DATA)); feats=[c for c in df.columns if c not in ('year','target')]
    src=df[df.year<=2013].reset_index(drop=True); targets={y:df[df.year==y].reset_index(drop=True) for y in (2014,2015)}
    rows=[]; solvers=[]; bwrows=[]; splitrows=[]
    for rep in range(rep_start,min(rep_end,REPS)):
        srng=np.random.default_rng(dseed(rep,10)); itr,ical=sample_disjoint(srng,len(src),[N_TRAIN,N_CAL])
        Xtr=src.loc[itr,feats].to_numpy(float); ytr=src.loc[itr,'target'].to_numpy(float); Xcal=src.loc[ical,feats].to_numpy(float); ycal=src.loc[ical,'target'].to_numpy(float)
        xsc=StandardScaler().fit(Xtr); Xtr_s=xsc.transform(Xtr); Xcal_s=xsc.transform(Xcal); ymu=float(ytr.mean()); ysd=float(ytr.std(ddof=0)); ysd=ysd if ysd>0 else 1.; ytr_s=(ytr-ymu)/ysd; ycal_s=(ycal-ymu)/ysd
        base_model=OracleWeightedSplitConformalRidge(ALPHA).fit(Xtr_s,ytr_s,Xcal_s,ycal_s)
        drng=np.random.default_rng(dseed(rep,20)); dens_idx=drng.choice(len(Xtr),size=N_DENS,replace=False); Xdens_s=Xtr_s[dens_idx]
        h,hinfo=rlcp_select_h(Xtr_s,dseed(rep,30)); bwrows.append({'rep':rep,'h':h,**hinfo})
        for year in (2014,2015):
            td=targets[year]; trng=np.random.default_rng(dseed(rep,year,40)); iu,itc,itest=sample_disjoint(trng,len(td),[N_TARGET_UNLAB,N_TARGET_CAL,N_TEST])
            Xu=td.loc[iu,feats].to_numpy(float); Xtc=td.loc[itc,feats].to_numpy(float); ytc=td.loc[itc,'target'].to_numpy(float); Xt=td.loc[itest,feats].to_numpy(float); yt=td.loc[itest,'target'].to_numpy(float)
            Xu_s=xsc.transform(Xu); Xtc_s=xsc.transform(Xtc); Xt_s=xsc.transform(Xt); ytc_s=(ytc-ymu)/ysd; yt_s=(yt-ymu)/ysd
            base={'layer':'natural_temporal','rep':rep,'target_year':year,'source_years':'2011-2013'}
            shift_mmd=rbf_mmd2(Xcal_s,Xt_s,max_points=300)
            pred=base_model.model.predict(Xt_s); point_rmse=float(np.sqrt(mean_squared_error(yt_s,pred)))
            lo,hi=base_model.predict_interval(Xt_s); met=interval_metrics(yt_s,lo,hi,ALPHA); rows.append({**base,'method':'SCP-Ridge',**met,'ess_ratio':1.0,'information_loss':0.0,'domain_auc':np.nan,'mmd2':shift_mmd,'point_rmse':point_rmse})
            logit=fit_density_ratio(Xdens_s,Xu_s,C=.1); wc=logit.ratio(Xcal_s); wt=logit.ratio(Xt_s); diag=weight_diagnostics(wc); auc=float(roc_auc_score(np.r_[np.zeros(len(Xcal_s)),np.ones(len(Xt_s))],np.r_[logit.probabilities(Xcal_s),logit.probabilities(Xt_s)]))
            lo,hi=base_model.predict_interval_weighted(Xt_s,wc,wt); met=interval_metrics(yt_s,lo,hi,ALPHA); rows.append({**base,'method':'Estimated-WCP-Logit',**met,**diag,'information_loss':1-diag['ess_ratio'],'domain_auc':auc,'mmd2':shift_mmd,'point_rmse':point_rmse})
            hgb=fit_hgb_ratio(Xdens_s,Xu_s,dseed(rep,year,50)); wc=hgb.ratio(Xcal_s); wt=hgb.ratio(Xt_s); diag=weight_diagnostics(wc); auc=float(roc_auc_score(np.r_[np.zeros(len(Xcal_s)),np.ones(len(Xt_s))],np.r_[hgb.probabilities(Xcal_s),hgb.probabilities(Xt_s)]))
            lo,hi=base_model.predict_interval_weighted(Xt_s,wc,wt); met=interval_metrics(yt_s,lo,hi,ALPHA); rows.append({**base,'method':'Estimated-WCP-HGB',**met,**diag,'information_loss':1-diag['ess_ratio'],'domain_auc':auc,'mmd2':shift_mmd,'point_rmse':point_rmse})
            sig,bwi=kmm.select_sigma(Xcal_s,Xu_s,dseed(rep,year,60)); wk,info=kmm.kmm_solve(Xcal_s,Xu_s,sig,B=kmm.B); qk=kmm.weighted_quantile(base_model.cal_scores,wk,1-ALPHA); met=external_interval_metrics(yt_s,pred,np.full(len(Xt_s),qk)); diag=weight_diagnostics(wk); rows.append({**base,'method':'KMM-CP-Ridge',**met,**diag,'information_loss':1-diag['ess_ratio'],'domain_auc':np.nan,'mmd2':shift_mmd,'point_rmse':point_rmse}); solvers.append({**base,'sigma':sig,**bwi,**info})
            qr,rdiag=rlcp_thresholds(Xcal_s,base_model.cal_scores,Xt_s,h,dseed(rep,year,70)); met=external_interval_metrics(yt_s,pred,qr); rows.append({**base,'method':'RLCP-Ridge',**met,'ess_ratio':np.nan,'information_loss':np.nan,'domain_auc':np.nan,'mmd2':shift_mmd,'point_rmse':point_rmse,**rdiag})
            lo,hi=target_cal_interval(base_model,Xtc_s,ytc_s,Xt_s); met=interval_metrics(yt_s,lo,hi,ALPHA); rows.append({**base,'method':'Target-Cal-SCP-Reference',**met,'ess_ratio':1.0,'information_loss':0.0,'domain_auc':np.nan,'mmd2':shift_mmd,'point_rmse':point_rmse})
            splitrows.append({**base,'n_source_train':N_TRAIN,'n_source_cal':N_CAL,'n_source_density':N_DENS,'n_target_unlabeled':N_TARGET_UNLAB,'n_target_labeled_reference_cal':N_TARGET_CAL,'n_target_test':N_TEST})
        print('P06 rep',rep,flush=True)
    return pd.DataFrame(rows),pd.DataFrame(solvers),pd.DataFrame(bwrows),pd.DataFrame(splitrows)

def paired_ci(d):
    d=np.asarray(d,float); d=d[np.isfinite(d)]; n=len(d); m=float(d.mean()) if n else np.nan
    if n<2:return n,m,np.nan,np.nan
    se=float(d.std(ddof=1)/math.sqrt(n)); c=float(t.ppf(.975,n-1)); return n,m,m-c*se,m+c*se

def summarize(raw,sol,bw,splits):
    raw.to_csv(OUT/'raw_p06_temporal.csv',index=False); sol.to_csv(OUT/'kmm_solver_p06.csv',index=False); bw.to_csv(OUT/'rlcp_bandwidth_p06.csv',index=False); splits.to_csv(OUT/'split_manifest_p06.csv',index=False)
    summ=raw.groupby(['target_year','method'],as_index=False).agg(coverage=('coverage','mean'),coverage_sd=('coverage','std'),coverage_deficit=('coverage_deficit','mean'),coverage_gap=('coverage_gap','mean'),width=('mean_width_finite','mean'),interval_score=('interval_score_finite','mean'),inf_fraction=('infinite_interval_fraction','mean'),ess_ratio=('ess_ratio','mean'),domain_auc=('domain_auc','mean'),mmd2=('mmd2','mean'),point_rmse=('point_rmse','mean'))
    summ.to_csv(OUT/'summary_p06_temporal.csv',index=False)
    contrasts=[]
    for year in (2014,2015):
        g=raw[raw.target_year==year]
        piv=g.pivot(index='rep',columns='method',values=['coverage_deficit','coverage_gap','mean_width_finite','interval_score_finite'])
        for method in [m for m in g.method.unique() if m!='SCP-Ridge']:
            for metric in ['coverage_deficit','coverage_gap','mean_width_finite','interval_score_finite']:
                P=piv[metric]
                if method in P and 'SCP-Ridge' in P:
                    n,m,lo,hi=paired_ci((P[method]-P['SCP-Ridge']).dropna()); contrasts.append({'contrast_type':'method_minus_scp','target_year':year,'method':method,'metric':metric,'n':n,'mean_difference':m,'ci95_low':lo,'ci95_high':hi})
    for method in raw.method.unique():
        g=raw[raw.method==method].pivot(index='rep',columns='target_year',values=['coverage_deficit','coverage_gap','mean_width_finite','interval_score_finite'])
        for metric in ['coverage_deficit','coverage_gap','mean_width_finite','interval_score_finite']:
            P=g[metric]
            if 2014 in P and 2015 in P:
                n,m,lo,hi=paired_ci((P[2015]-P[2014]).dropna()); contrasts.append({'contrast_type':'2015_minus_2014','target_year':2015,'method':method,'metric':metric,'n':n,'mean_difference':m,'ci95_low':lo,'ci95_high':hi})
    pd.DataFrame(contrasts).to_csv(OUT/'paired_contrasts_p06.csv',index=False)
    qa={'rows':len(raw),'repetitions':int(raw.rep.nunique()),'target_years':sorted(raw.target_year.unique().tolist()),'methods':sorted(raw.method.unique().tolist()),'duplicate_keys':int(raw.duplicated(['rep','target_year','method']).sum()),'coverage_outside_0_1':int(((raw.coverage<0)|(raw.coverage>1)).sum()),'kmm_solver_rows':len(sol),'kmm_pg_over_1e4':int((sol.pg_residual>1e-4).sum()) if len(sol) else 0,'canonical_sha256':sha256(DATA),'year_counts':YEAR_COUNTS}
    (OUT/'qa_p06.json').write_text(json.dumps(qa,indent=2))
    manifest={'version':'P0-6-v1','purpose':'natural temporal deployment shift without engineered tilting','dataset':'UCI Gas Turbine CO and NOx Emission Data Set','doi':'10.24432/C5WC95','split':'2011-2013 source; 2014 and 2015 natural target years','source_protocol':'UCI-recommended first three years train/CV and last two years test','year_counts':YEAR_COUNTS,'predictors':['AT','AP','AH','AFDP','GTEP','TIT','TAT','TEY','CDP'],'target':'NOx','methods':sorted(raw.method.unique().tolist()),'budgets':{'source_train':N_TRAIN,'source_calibration':N_CAL,'density_source':N_DENS,'target_unlabeled':N_TARGET_UNLAB,'target_labeled_reference_calibration':N_TARGET_CAL,'target_test':N_TEST},'note':'Target-Cal-SCP-Reference uses target labels only as a non-deployable diagnostic; all practical correction methods are label-free on target. Natural temporal layer may contain conditional as well as covariate drift and is not treated as an exact covariate-shift experiment.','input_sha256':sha256(DATA)}
    (OUT/'manifest_p06.json').write_text(json.dumps(manifest,indent=2))
    checks=[]
    for p in sorted(OUT.iterdir()):
        if p.is_file() and p.name!='checksums_p06.json': checks.append({'file':p.name,'sha256':sha256(p),'bytes':p.stat().st_size})
    (OUT/'checksums_p06.json').write_text(json.dumps(checks,indent=2))
    print('\nSUMMARY\n',summ.to_string(index=False)); print('\nQA\n',json.dumps(qa,indent=2))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--rep-start',type=int,default=0); ap.add_argument('--rep-end',type=int,default=REPS); a=ap.parse_args(); t0=time.time(); raw,sol,bw,splits=run(a.rep_start,a.rep_end); summarize(raw,sol,bw,splits); print('seconds',time.time()-t0)
if __name__=='__main__':main()
