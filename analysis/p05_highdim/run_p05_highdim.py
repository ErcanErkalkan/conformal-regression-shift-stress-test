from __future__ import annotations
import argparse, hashlib, json, math, sys, time, warnings
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import t
from sklearn.exceptions import ConvergenceWarning
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SYN = REPO/'synthetic'
sys.path.insert(0, str(SYN/'src'))
from cpshift.conformal import OracleWeightedSplitConformalRidge
from cpshift.data_v10 import oracle_density_ratio, response_signal, mean_shift_vector, variance_scale, mixture_params, tail_mixture_params
from cpshift.density_ratio import ClassifierDensityRatio
from cpshift.metrics import interval_metrics, normalized_weight_error, weight_diagnostics
from cpshift.runner_v10 import derived_seed

MASTER=2026081601
ALPHA=0.10
DIMS=(5,20,50,100)
MAXP=max(DIMS)
FAMILIES=('mean','variance','mixture','tail_mixture')
SEVERITIES=(0.0,1.0,2.0)
N_TRAIN=1000; N_CAL=1000; N_TEST=2500; N_U=1000
RATIO_DEGREE=2; RATIO_C=0.1; RATIO_MAX_ITER=400
REGIMES=(('linear','gaussian','dimension_isolation',SEVERITIES),)

def response_from_z(X,dgp,noise,z):
    sig=response_signal(np.asarray(X,float),dgp)
    z=np.asarray(z,float)
    if noise=='gaussian': eps=z
    elif noise=='heteroscedastic': eps=(0.5+0.5*np.abs(X[:,0]))*z
    else: raise ValueError(noise)
    return sig+eps

def shifted_from_latent(Z,p,family,severity,flags=None,Zfar=None):
    X=np.asarray(Z[:,:p],float).copy(); sev=float(severity)
    if sev==0.0: return X
    if family=='mean':
        X += mean_shift_vector(sev,p)
    elif family=='variance':
        X *= variance_scale(sev)
    elif family=='mixture':
        if flags is None: raise ValueError('mixture flags required')
        _,mu=mixture_params(sev,p); X[np.asarray(flags,bool)] += mu
    elif family=='tail_mixture':
        if flags is None or Zfar is None: raise ValueError('tail latent required')
        _,s=tail_mixture_params(sev); f=np.asarray(flags,bool); X[f]=np.asarray(Zfar[f,:p],float)*s
    else: raise ValueError(family)
    return X

def target_latents(rep,reg_idx,fam_idx,sev_idx,family,severity,n,stream):
    seed=derived_seed(MASTER, 5005, rep, reg_idx, fam_idx, sev_idx, stream)
    rng=np.random.default_rng(seed)
    Z=rng.normal(size=(n,MAXP))
    flags=None; Zfar=None
    if family=='mixture' and severity>0:
        pi,_=mixture_params(severity,MAXP); flags=rng.random(n)<pi
    elif family=='tail_mixture' and severity>0:
        pi,_=tail_mixture_params(severity); flags=rng.random(n)<pi; Zfar=rng.normal(size=(n,MAXP))
    return Z,flags,Zfar,seed

def source_latents(rep,reg_idx):
    seed=derived_seed(MASTER,5005,rep,reg_idx,100)
    rng=np.random.default_rng(seed)
    Xtr=rng.normal(size=(N_TRAIN,MAXP)); Xcal=rng.normal(size=(N_CAL,MAXP))
    ztr=rng.normal(size=N_TRAIN); zcal=rng.normal(size=N_CAL)
    return Xtr,Xcal,ztr,zcal,seed

def record(rows,base,method,met,diag,extra):
    rows.append({**base,'method':method,**met,**diag,**extra})

def run_rep(rep:int):
    rows=[]
    for reg_idx,(dgp,noise,layer,severities) in enumerate(REGIMES):
        XtrM,XcalM,ztr,zcal,source_seed=source_latents(rep,reg_idx)
        Xtr5=XtrM[:,:5]; Xcal5=XcalM[:,:5]
        ytr=response_from_z(Xtr5,dgp,noise,ztr); ycal=response_from_z(Xcal5,dgp,noise,zcal)
        base_model=OracleWeightedSplitConformalRidge(alpha=ALPHA).fit(Xtr5,ytr,Xcal5,ycal)
        models={p:(base_model,XtrM[:,:p],XcalM[:,:p],ytr,ycal) for p in DIMS}
        baseline_cache={}
        ZU0,fu0,zfu0,u0seed=target_latents(rep,reg_idx,0,0,FAMILIES[0],0.0,N_U,301)
        ZT0,ft0,zft0,t0seed=target_latents(rep,reg_idx,0,0,FAMILIES[0],0.0,N_TEST,302)
        znoise0=np.random.default_rng(derived_seed(MASTER,5005,rep,reg_idx,0,0,303)).normal(size=N_TEST)
        for fi,fam in enumerate(FAMILIES):
            for si,sev in enumerate(severities):
                sev=float(sev)
                if sev==0.0:
                    ZU,fu,zfu,useed=ZU0,fu0,zfu0,u0seed; ZT,ft,zft,tseed=ZT0,ft0,zft0,t0seed; znoise=znoise0
                else:
                    canon_si=SEVERITIES.index(sev)
                    ZU,fu,zfu,useed=target_latents(rep,reg_idx,fi,canon_si,fam,sev,N_U,301)
                    ZT,ft,zft,tseed=target_latents(rep,reg_idx,fi,canon_si,fam,sev,N_TEST,302)
                    znoise=np.random.default_rng(derived_seed(MASTER,5005,rep,reg_idx,fi,canon_si,303)).normal(size=N_TEST)
                for p in DIMS:
                    model,Xtr,Xcal,ytr,ycal=models[p]
                    Xu=shifted_from_latent(ZU,p,fam,sev,fu,zfu)
                    Xt=shifted_from_latent(ZT,p,fam,sev,ft,zft)
                    yt=response_from_z(Xt,dgp,noise,znoise)
                    base={'layer':layer,'rep':rep,'dgp':dgp,'noise':noise,'dimension':p,'shift_family':fam,'severity':sev,
                          'source_seed':source_seed,'target_unlabeled_seed':useed,'target_test_seed':tseed,
                          'poly_feature_count':int((p*p+3*p)//2)}
                    if sev==0.0 and p in baseline_cache:
                        for method,met,diag,extra in baseline_cache[p]: record(rows,base,method,met,diag,extra)
                        continue
                    unweighted={'ess':N_CAL,'ess_ratio':1.0,'weight_cv':0.0,'max_normalized_weight':1.0/N_CAL}
                    condition=[]
                    lo,hi=model.predict_interval(Xt[:,:5])
                    met=interval_metrics(yt,lo,hi,ALPHA); extra={'shift_classifier_auc':np.nan,'log_weight_rmse':np.nan,'log_weight_mae':np.nan,'log_weight_corr':np.nan,'estimated_to_oracle_ess_ratio':np.nan,'ratio_fit_seconds':0.0,'ratio_converged':True,'ratio_n_iter':0}
                    record(rows,base,'SCP-Ridge',met,unweighted,extra); condition.append(('SCP-Ridge',met,unweighted,extra))
                    wo_cal=oracle_density_ratio(Xcal,fam,sev); wo_test=oracle_density_ratio(Xt,fam,sev)
                    odiag=weight_diagnostics(wo_cal); lo,hi=model.predict_interval_weighted(Xt[:,:5],wo_cal,wo_test)
                    met=interval_metrics(yt,lo,hi,ALPHA); extra={'shift_classifier_auc':np.nan,'log_weight_rmse':0.0,'log_weight_mae':0.0,'log_weight_corr':1.0,'estimated_to_oracle_ess_ratio':1.0,'ratio_fit_seconds':0.0,'ratio_converged':True,'ratio_n_iter':0}
                    record(rows,base,'Oracle-WCP-Ridge',met,odiag,extra); condition.append(('Oracle-WCP-Ridge',met,odiag,extra))
                    est_seed=derived_seed(MASTER,5005,rep,reg_idx,fi,SEVERITIES.index(sev),401,p)
                    tfit=time.perf_counter(); conv=True
                    with warnings.catch_warnings(record=True) as caught:
                        warnings.simplefilter('always',ConvergenceWarning)
                        est=ClassifierDensityRatio(max_iter=RATIO_MAX_ITER,random_state=est_seed,degree=RATIO_DEGREE,C=RATIO_C).fit(Xtr,Xu)
                        if any(issubclass(w.category,ConvergenceWarning) for w in caught): conv=False
                    fitsec=time.perf_counter()-tfit
                    ps=est.model.predict_proba(Xcal)[:,1]; pt=est.model.predict_proba(Xt)[:,1]
                    auc=float(roc_auc_score(np.r_[np.zeros(len(ps),dtype=int),np.ones(len(pt),dtype=int)],np.r_[ps,pt]))
                    ps=np.clip(ps,1e-5,1-1e-5); pt=np.clip(pt,1e-5,1-1e-5); prior=est.prior_ratio
                    we_cal=prior*ps/(1-ps); we_test=prior*pt/(1-pt)
                    ediag=weight_diagnostics(we_cal); werr=normalized_weight_error(we_cal,wo_cal)
                    lo,hi=model.predict_interval_weighted(Xt[:,:5],we_cal,we_test); niter=int(np.max(est.model.named_steps['logit'].n_iter_))
                    met=interval_metrics(yt,lo,hi,ALPHA); extra={'shift_classifier_auc':auc,**werr,'ratio_fit_seconds':fitsec,'ratio_converged':bool(conv),'ratio_n_iter':niter}
                    record(rows,base,'Estimated-WCP-Primary',met,ediag,extra); condition.append(('Estimated-WCP-Primary',met,ediag,extra))
                    if sev==0.0: baseline_cache[p]=condition
    return pd.DataFrame(rows)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--rep-start',type=int,default=0); ap.add_argument('--rep-end',type=int,default=30); ap.add_argument('--out',required=True)
    a=ap.parse_args(); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    allr=[]; t0=time.time()
    for rep in range(a.rep_start,a.rep_end):
        df=run_rep(rep); allr.append(df); print(f'P05 rep {rep} rows={len(df)} elapsed={time.time()-t0:.1f}s',flush=True)
    raw=pd.concat(allr,ignore_index=True)
    key=['layer','rep','dimension','shift_family','severity','method']
    assert raw.duplicated(key).sum()==0
    raw.to_csv(out/f'raw_p05_rep{a.rep_start:02d}_{a.rep_end:02d}.csv',index=False)
    meta={'rep_start':a.rep_start,'rep_end':a.rep_end,'rows':len(raw),'seconds':time.time()-t0,'version':'P0-5-v1'}
    (out/f'meta_p05_rep{a.rep_start:02d}_{a.rep_end:02d}.json').write_text(json.dumps(meta,indent=2))
    print(json.dumps(meta,indent=2),flush=True)
if __name__=='__main__': main()
