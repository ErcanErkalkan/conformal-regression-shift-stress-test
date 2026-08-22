from __future__ import annotations
import json, math, hashlib, time, sys
from pathlib import Path
import numpy as np, pandas as pd, yaml
from scipy.spatial.distance import cdist, pdist
from scipy.stats import t
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

# In the manuscript supplement this script is packaged beside frozen synthetic/real
# source snapshots. In the repository, run from a checkout after adjusting these
# two roots if the frozen sources are not mirrored beneath this analysis folder.
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
SYNTH_ROOT=REPO/'synthetic'
REAL_ROOT=REPO/'real_data'
OUT=HERE/'results'; OUT.mkdir(parents=True,exist_ok=True)
DATA={k:REAL_ROOT/'data'/'canonical'/f'{k}.csv' for k in ['ccpp','appliances','superconductivity','gas_turbine_nox','online_news']}
ALPHA=0.10
ULSIF_CENTERS=80
ULSIF_SIGMA_FACTORS=(0.5,1.0,2.0)
ULSIF_LAMBDAS=(1e-3,1e-2,1e-1)
HGB_PARAMS=dict(max_iter=100,learning_rate=0.08,max_leaf_nodes=15,min_samples_leaf=20,l2_regularization=1.0,early_stopping=True,validation_fraction=0.15,n_iter_no_change=8,tol=1e-5)

sys.path.insert(0,str(SYNTH_ROOT/'src'))
from cpshift.runner_v10 import derived_seed
from cpshift.data_v10 import generate_source_split, sample_target_covariates, generate_target, oracle_density_ratio
from cpshift.conformal import OracleWeightedSplitConformalRidge
from cpshift.density_ratio import ClassifierDensityRatio
from cpshift.metrics import interval_metrics as synth_interval_metrics, weight_diagnostics as synth_weight_diagnostics, normalized_weight_error as synth_nwe

sys.path.insert(0,str(REAL_ROOT))
from shift_design import fit_directional_basis, fit_radial_basis, radial_score, paired_split_indices, sample_target_indices, derive_seed, tilt_ratio, tilt_sampling_probabilities
from density_ratio import fit_density_ratio
from metrics_core import interval_metrics as real_interval_metrics, weight_diagnostics as real_weight_diagnostics, normalized_weight_error as real_nwe
from conformal_core import OracleWeightedSplitConformalRidge as RealWCP


def sha256(p:Path):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1<<20),b''): h.update(c)
    return h.hexdigest()

class ClassifierOddsRatio:
    def __init__(self, model, prior_ratio:float, source_mean:float, clip:float=1e-5):
        self.model=model; self.prior_ratio=float(prior_ratio); self.source_mean=float(source_mean); self.clip=float(clip)
    def probabilities(self,X): return self.model.predict_proba(np.asarray(X,float))[:,1]
    def ratio(self,X):
        p=np.clip(self.probabilities(X),self.clip,1-self.clip)
        r=self.prior_ratio*p/(1-p)
        return r/max(self.source_mean,1e-12)


def fit_hgb_ratio(Xs,Xt,seed,clip=1e-5):
    Xs=np.asarray(Xs,float); Xt=np.asarray(Xt,float)
    X=np.vstack([Xs,Xt]); y=np.r_[np.zeros(len(Xs),int),np.ones(len(Xt),int)]
    model=HistGradientBoostingClassifier(random_state=int(seed),**HGB_PARAMS).fit(X,y)
    prior=float(len(Xs)/len(Xt))
    ps=np.clip(model.predict_proba(Xs)[:,1],clip,1-clip)
    source_mean=float(np.mean(prior*ps/(1-ps)))
    return ClassifierOddsRatio(model,prior,source_mean,clip)

class ULSIFRatio:
    def __init__(self,scaler,centers,sigma,alpha,source_mean):
        self.scaler=scaler; self.centers=centers; self.sigma=float(sigma); self.alpha=alpha; self.source_mean=float(source_mean)
    def _phi(self,X):
        Z=self.scaler.transform(np.asarray(X,float)); d2=cdist(Z,self.centers,'sqeuclidean')
        return np.exp(-d2/(2*self.sigma*self.sigma))
    def ratio(self,X):
        r=self._phi(X)@self.alpha
        r=np.clip(r,1e-8,None)
        return r/max(self.source_mean,1e-12)


def _ulsif_fit_fixed(S,T,C,sigma,lam):
    PhiS=np.exp(-cdist(S,C,'sqeuclidean')/(2*sigma*sigma))
    PhiT=np.exp(-cdist(T,C,'sqeuclidean')/(2*sigma*sigma))
    H=(PhiS.T@PhiS)/len(S); h=PhiT.mean(axis=0)
    A=H+float(lam)*np.eye(len(C))
    try: alpha=np.linalg.solve(A,h)
    except np.linalg.LinAlgError: alpha=np.linalg.lstsq(A,h,rcond=None)[0]
    return np.clip(alpha,0,None)


def fit_ulsif_ratio(Xs,Xt,seed,n_centers=ULSIF_CENTERS):
    Xs=np.asarray(Xs,float); Xt=np.asarray(Xt,float)
    scaler=StandardScaler().fit(Xs); S=scaler.transform(Xs); T=scaler.transform(Xt)
    rng=np.random.default_rng(int(seed))
    ps=rng.permutation(len(S)); pt=rng.permutation(len(T)); ns=max(20,int(.8*len(S))); nt=max(20,int(.8*len(T)))
    Sf,Sv=S[ps[:ns]],S[ps[ns:]]; Tf,Tv=T[pt[:nt]],T[pt[nt:]]
    ids=rng.choice(len(Tf),size=min(n_centers,len(Tf)),replace=False); C0=Tf[ids]
    zi=np.vstack([Sf[np.linspace(0,len(Sf)-1,min(100,len(Sf)),dtype=int)],Tf[np.linspace(0,len(Tf)-1,min(100,len(Tf)),dtype=int)]])
    ds=pdist(zi,'euclidean'); ds=ds[ds>1e-12]; base_sigma=max(float(np.median(ds)) if len(ds) else 1.0,1e-3)
    best=None
    for f in ULSIF_SIGMA_FACTORS:
        sig=max(base_sigma*float(f),1e-3)
        PhiSv=np.exp(-cdist(Sv,C0,'sqeuclidean')/(2*sig*sig)); PhiTv=np.exp(-cdist(Tv,C0,'sqeuclidean')/(2*sig*sig))
        for lam in ULSIF_LAMBDAS:
            a=_ulsif_fit_fixed(Sf,Tf,C0,sig,float(lam))
            rs=np.clip(PhiSv@a,0,None); rt=np.clip(PhiTv@a,0,None)
            risk=float(0.5*np.mean(rs*rs)-np.mean(rt))
            cand=(risk,abs(math.log10(float(f))),abs(math.log10(float(lam))+2),float(f),float(lam))
            if best is None or cand[:3] < best[:3]: best=cand
    _,_,_,factor,lam=best
    ids=rng.choice(len(T),size=min(n_centers,len(T)),replace=False); C=T[ids]
    zall=np.vstack([S[np.linspace(0,len(S)-1,min(120,len(S)),dtype=int)],T[np.linspace(0,len(T)-1,min(120,len(T)),dtype=int)]])
    ds=pdist(zall,'euclidean'); ds=ds[ds>1e-12]; full_base=max(float(np.median(ds)) if len(ds) else 1.0,1e-3); sigma=full_base*factor
    alpha=_ulsif_fit_fixed(S,T,C,sigma,lam)
    raw=np.clip(np.exp(-cdist(S,C,'sqeuclidean')/(2*sigma*sigma))@alpha,1e-8,None); sm=float(raw.mean())
    return ULSIFRatio(scaler,C,sigma,alpha,sm), {'sigma':sigma,'sigma_factor':factor,'centers':len(C),'lambda':lam,'validation_risk':best[0],'positive_alpha':int(np.sum(alpha>0)),'alpha_l1':float(alpha.sum())}


def domain_auc_ratio(model,Xs_hold,Xt_hold):
    rs=model.ratio(Xs_hold); rt=model.ratio(Xt_hold)
    y=np.r_[np.zeros(len(rs),int),np.ones(len(rt),int)]; score=np.r_[rs,rt]
    return float(roc_auc_score(y,score))


def record_weighted(rows,base,label,wcp,Xt,yt,wec,wet,metrics,oracle_c=None,auc=np.nan,fitinfo=None):
    diag=metrics['weight'](wec); werr=metrics['nwe'](wec,oracle_c) if oracle_c is not None else {}
    lo,hi=wcp.predict_interval_weighted(Xt,wec,wet); im=metrics['interval'](yt,lo,hi,ALPHA)
    im['empty_interval_fraction']=0.0
    r={**base,'method':label,'domain_auc':auc,**im,**diag,**werr,'information_loss':1-diag['ess_ratio']}
    if fitinfo:
        for k,v in fitinfo.items(): r[f'est_{k}']=v
    rows.append(r)


def path_areas(df,group_cols):
    out=[]
    for key,g in df.groupby(group_cols+['method']):
        key=key if isinstance(key,tuple) else (key,); g=g.sort_values('severity'); x=g.severity.to_numpy(float)
        r={c:v for c,v in zip(group_cols+['method'],key)}
        for col,name in [('coverage_deficit','A_cov'),('coverage_gap','A_gap'),('information_loss','A_info'),('log_weight_rmse','A_wrmse')]:
            vals=g[col].to_numpy(float) if col in g else np.full(len(g),np.nan)
            r[name]=float(np.trapezoid(vals,x)) if np.isfinite(vals).all() else np.nan
        r['A_inf']=float(np.trapezoid(g['infinite_interval_fraction'].fillna(0).to_numpy(float),x))
        out.append(r)
    return pd.DataFrame(out)


def run_synthetic(rep_start=0,rep_end=None):
    cfg=yaml.safe_load((SYNTH_ROOT/'configs/main_v10_locked.yaml').read_text()); master=int(cfg['seed']); p=int(cfg['n_features'])
    dgp='nonlinear'; noise='heteroscedastic'; di=cfg['dgp_types'].index(dgp); ni=cfg['noise_types'].index(noise)
    end=int(cfg['repetitions']) if rep_end is None else int(rep_end); rows=[]
    for rep in range(int(rep_start),end):
        rng=np.random.default_rng(derived_seed(master,rep,di,ni,100)); Xtr,ytr,Xcal,ycal=generate_source_split(rng,int(cfg['n_train']),int(cfg['n_cal']),p,dgp,noise)
        wcp=OracleWeightedSplitConformalRidge(ALPHA).fit(Xtr,ytr,Xcal,ycal)
        bXu=sample_target_covariates(np.random.default_rng(derived_seed(master,rep,di,ni,0,0,301)),int(cfg['n_target_unlabeled']),p,cfg['shift_families'][0],0.0)
        bXt,byt=generate_target(np.random.default_rng(derived_seed(master,rep,di,ni,0,0,302)),int(cfg['n_test']),p,cfg['shift_families'][0],0.0,dgp,noise)
        for fi,fam in enumerate(cfg['shift_families']):
            for si,sev0 in enumerate(cfg['severities']):
                sev=float(sev0)
                if sev==0: Xu,Xt,yt=bXu,bXt,byt
                else:
                    Xu=sample_target_covariates(np.random.default_rng(derived_seed(master,rep,di,ni,fi,si,301)),int(cfg['n_target_unlabeled']),p,fam,sev)
                    Xt,yt=generate_target(np.random.default_rng(derived_seed(master,rep,di,ni,fi,si,302)),int(cfg['n_test']),p,fam,sev,dgp,noise)
                base={'layer':'synthetic','rep':rep,'dgp':dgp,'noise':noise,'scenario':fam,'severity':sev}
                wo_c=oracle_density_ratio(Xcal,fam,sev); wo_t=oracle_density_ratio(Xt,fam,sev)
                mets={'weight':synth_weight_diagnostics,'nwe':synth_nwe,'interval':synth_interval_metrics}
                logit=ClassifierDensityRatio(max_iter=int(cfg['density_ratio_max_iter']),random_state=derived_seed(master,rep,di,ni,fi,si,401),degree=int(cfg['primary_density_ratio']['degree']),C=float(cfg['primary_density_ratio']['C'])).fit(Xtr,Xu)
                wc=logit.ratio(Xcal); wt=logit.ratio(Xt); auc=float(logit.heldout_auc(Xcal,Xt))
                record_weighted(rows,base,'Estimated-WCP-Logit',wcp,Xt,yt,wc,wt,mets,wo_c,auc)
                hgb=fit_hgb_ratio(Xtr,Xu,derived_seed(master,rep,di,ni,fi,si,511))
                wc=hgb.ratio(Xcal); wt=hgb.ratio(Xt); auc=float(roc_auc_score(np.r_[np.zeros(len(Xcal),int),np.ones(len(Xt),int)],np.r_[hgb.probabilities(Xcal),hgb.probabilities(Xt)]))
                record_weighted(rows,base,'Estimated-WCP-HGB',wcp,Xt,yt,wc,wt,mets,wo_c,auc,HGB_PARAMS)
                ul,info=fit_ulsif_ratio(Xtr,Xu,derived_seed(master,rep,di,ni,fi,si,611))
                wc=ul.ratio(Xcal); wt=ul.ratio(Xt); auc=domain_auc_ratio(ul,Xcal,Xt)
                record_weighted(rows,base,'Estimated-WCP-uLSIF',wcp,Xt,yt,wc,wt,mets,wo_c,auc,info)
                if fam != 'nonlinear' and wo_c is not None and wo_t is not None:
                    record_weighted(rows,base,'Oracle-WCP-Ridge',wcp,Xt,yt,wo_c,wo_t,mets,wo_c,np.nan)
        print('P03 synth rep',rep,flush=True)
    return pd.DataFrame(rows)


def run_public(rep_start=0,rep_end=None,datasets=None):
    cfg=json.loads((REAL_ROOT/'configs/real_data_prelock.json').read_text()); master=int(cfg['master_seed']); rows=[]
    order=['ccpp','appliances','superconductivity','gas_turbine_nox','online_news']; datasets=order if datasets is None else datasets
    end=int(cfg['repetitions']) if rep_end is None else int(rep_end)
    for key in datasets:
        didx=order.index(key); df=pd.read_csv(DATA[key]); X=df.drop(columns=['target']).to_numpy(float); y=df.target.to_numpy(float); n=len(X)
        for rep in range(int(rep_start),end):
            split_seed=derive_seed(master,didx,rep,0,10); it,ic,ir=paired_split_indices(n,split_seed,float(cfg['split_fractions']['train']),float(cfg['split_fractions']['calibration']))
            Xtr,ytr=X[it],y[it]; Xcal,ycal=X[ic],y[ic]; Xres,yres=X[ir],y[ir]
            xsc=StandardScaler().fit(Xtr); Xtr_s=xsc.transform(Xtr); Xcal_s=xsc.transform(Xcal)
            ymu=float(ytr.mean()); ysd=float(ytr.std(ddof=0)); ysd=ysd if ysd>0 else 1.0
            ytr_s=(ytr-ymu)/ysd; ycal_s=(ycal-ymu)/ysd
            wcp=RealWCP(ALPHA).fit(Xtr_s,ytr_s,Xcal_s,ycal_s)
            dens_seed=derive_seed(master,didx,rep,0,30); drng=np.random.default_rng(dens_seed); dens_idx=drng.choice(len(Xtr),size=int(cfg['density_source_n']),replace=False); Xdens=Xtr[dens_idx]
            for mode in ['directional','radial']:
                if mode=='directional': basis=fit_directional_basis(Xtr,float(cfg['score_clip'])); score=lambda A:basis.score(A); sevs=cfg['directional_tilt_lambda']; modecode=0
                else: basis=fit_radial_basis(Xtr,float(cfg['score_clip'])); score=lambda A:radial_score(A,basis); sevs=cfg['radial_sensitivity_lambda']; modecode=1
                for si,sev0 in enumerate(sevs):
                    sev=float(sev0); probs=tilt_sampling_probabilities(score(Xres),sev)
                    iu,_=sample_target_indices(len(Xres),probs,int(cfg['target_unlabeled_n']),derive_seed(master,didx,rep,si,40)); ix,_=sample_target_indices(len(Xres),probs,int(cfg['target_test_n']),derive_seed(master,didx,rep,si,50))
                    Xu=Xres[iu]; Xt=Xres[ix]; yt=yres[ix]; Xt_s=xsc.transform(Xt); yt_s=(yt-ymu)/ysd
                    base={'layer':'public','dataset':key,'rep':rep,'scenario':mode,'severity':sev}
                    wo_c=tilt_ratio(score(Xcal),sev); wo_t=tilt_ratio(score(Xt),sev)
                    mets={'weight':real_weight_diagnostics,'nwe':real_nwe,'interval':real_interval_metrics}
                    logit=fit_density_ratio(Xdens,Xu,C=float(cfg['primary_density_ratio']['logistic_C']))
                    wc=logit.ratio(Xcal); wt=logit.ratio(Xt); auc=float(roc_auc_score(np.r_[np.zeros(len(Xcal),int),np.ones(len(Xt),int)],np.r_[logit.probabilities(Xcal),logit.probabilities(Xt)]))
                    record_weighted(rows,base,'Estimated-WCP-Logit',wcp,Xt_s,yt_s,wc,wt,mets,wo_c,auc)
                    hgb=fit_hgb_ratio(Xdens,Xu,derive_seed(master,didx,rep,si,511+100*modecode))
                    wc=hgb.ratio(Xcal); wt=hgb.ratio(Xt); auc=float(roc_auc_score(np.r_[np.zeros(len(Xcal),int),np.ones(len(Xt),int)],np.r_[hgb.probabilities(Xcal),hgb.probabilities(Xt)]))
                    record_weighted(rows,base,'Estimated-WCP-HGB',wcp,Xt_s,yt_s,wc,wt,mets,wo_c,auc,HGB_PARAMS)
                    ul,info=fit_ulsif_ratio(Xdens,Xu,derive_seed(master,didx,rep,si,611+100*modecode))
                    wc=ul.ratio(Xcal); wt=ul.ratio(Xt); auc=domain_auc_ratio(ul,Xcal,Xt)
                    record_weighted(rows,base,'Estimated-WCP-uLSIF',wcp,Xt_s,yt_s,wc,wt,mets,wo_c,auc,info)
                    record_weighted(rows,base,'Known-tilt-WCP-Ridge',wcp,Xt_s,yt_s,wo_c,wo_t,mets,wo_c,np.nan)
            print('P03 public',key,'rep',rep,flush=True)
    return pd.DataFrame(rows)


def summarize(syn,pub):
    syn.to_csv(OUT/'raw_p03_synthetic.csv',index=False); pub.to_csv(OUT/'raw_p03_public.csv',index=False)
    asyn=path_areas(syn,['rep','scenario']); apub=path_areas(pub,['dataset','rep','scenario'])
    asyn.to_csv(OUT/'path_areas_p03_synthetic.csv',index=False); apub.to_csv(OUT/'path_areas_p03_public.csv',index=False)
    ss=asyn.groupby(['scenario','method'],as_index=False).agg(A_cov=('A_cov','mean'),A_cov_sd=('A_cov','std'),A_gap=('A_gap','mean'),A_info=('A_info','mean'),A_wrmse=('A_wrmse','mean'),A_inf=('A_inf','mean'))
    sp=apub.groupby(['dataset','scenario','method'],as_index=False).agg(A_cov=('A_cov','mean'),A_cov_sd=('A_cov','std'),A_gap=('A_gap','mean'),A_info=('A_info','mean'),A_wrmse=('A_wrmse','mean'),A_inf=('A_inf','mean'))
    ss.to_csv(OUT/'area_summary_p03_synthetic.csv',index=False); sp.to_csv(OUT/'area_summary_p03_public.csv',index=False)
    rows=[]
    for layer,areas,groups,ref in [('synthetic',asyn,['scenario'],'Oracle-WCP-Ridge'),('public',apub,['dataset','scenario'],'Known-tilt-WCP-Ridge')]:
        for key,g in areas.groupby(groups):
            key=key if isinstance(key,tuple) else (key,); iddict=dict(zip(groups,key))
            piv=g.pivot(index=['rep'],columns='method',values='A_cov')
            for a,b in [('Estimated-WCP-HGB','Estimated-WCP-Logit'),('Estimated-WCP-uLSIF','Estimated-WCP-Logit'),('Estimated-WCP-Logit',ref),('Estimated-WCP-HGB',ref),('Estimated-WCP-uLSIF',ref)]:
                if a not in piv or b not in piv: continue
                d=(piv[a]-piv[b]).dropna().to_numpy(float); n=len(d); mean=float(d.mean()); sd=float(d.std(ddof=1)) if n>1 else np.nan; se=sd/math.sqrt(n) if n>1 else np.nan; crit=float(t.ppf(.975,n-1)) if n>1 else np.nan
                rows.append({'layer':layer,**iddict,'comparison':f'{a} - {b}','n':n,'mean_difference':mean,'ci95_low':mean-crit*se if n>1 else np.nan,'ci95_high':mean+crit*se if n>1 else np.nan})
    pd.DataFrame(rows).to_csv(OUT/'paired_Acov_contrasts_p03.csv',index=False)
    print('\nSYNTH\n',ss.to_string(index=False)); print('\nPUBLIC\n',sp.to_string(index=False))

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument('--smoke',action='store_true'); args=ap.parse_args()
    t0=time.time()
    if args.smoke:
        syn=run_synthetic(rep_start=0,rep_end=1); pub=run_public(rep_start=0,rep_end=1,datasets=['ccpp'])
    else:
        syn=run_synthetic(); pub=run_public()
    summarize(syn,pub); print('P03 total seconds',time.time()-t0)
