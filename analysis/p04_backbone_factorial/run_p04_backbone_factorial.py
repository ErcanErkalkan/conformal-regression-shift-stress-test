from __future__ import annotations
import argparse, json, math, sys, time, hashlib
from pathlib import Path
import numpy as np
import pandas as pd
import yaml
from scipy.stats import t
from sklearn.ensemble import GradientBoostingRegressor, HistGradientBoostingRegressor
from sklearn.linear_model import Ridge, QuantileRegressor
from sklearn.preprocessing import StandardScaler

HERE=Path(__file__).resolve().parent
P03=HERE.parent/'p03_density_estimator_expansion'
SYN=P03/'source'/'synthetic'
REAL=P03/'source'/'real'
DATA_DIR=Path(__import__('os').environ.get('P04_DATA_DIR', str(HERE/'data')))
DATA={k:DATA_DIR/f'{k}.csv' for k in ['ccpp','appliances','superconductivity','gas_turbine_nox','online_news']}
ALPHA=0.10
GBR_PARAMS=dict(loss='squared_error',n_estimators=80,learning_rate=0.1,max_depth=3)
PUBLIC_HGBR_PARAMS=dict(max_iter=80,learning_rate=0.1,max_leaf_nodes=15,max_depth=3,min_samples_leaf=20,l2_regularization=1.0,early_stopping=True,validation_fraction=0.15,n_iter_no_change=8,tol=1e-5)
CQR_LINEAR_ALPHA=0.0

sys.path.insert(0,str(SYN/'src'))
from cpshift.runner_v10 import derived_seed
from cpshift.data_v10 import generate_source_split, generate_target, sample_target_covariates, oracle_density_ratio
from cpshift.conformal import conformal_quantile, ConformalizedQuantileRegressor
from cpshift.metrics import interval_metrics as syn_metrics

sys.path.insert(0,str(REAL))
from shift_design import fit_directional_basis, fit_radial_basis, radial_score, paired_split_indices, sample_target_indices, derive_seed, tilt_ratio, tilt_sampling_probabilities
from metrics_core import interval_metrics as real_metrics


def sha256(p:Path):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1<<20),b''): h.update(c)
    return h.hexdigest()

class MeanConformal:
    def __init__(self,kind:str,seed:int=0):
        self.kind=kind
        if kind=='Ridge':
            self.model=Ridge(alpha=1.0)
        elif kind=='GBR':
            self.model=GradientBoostingRegressor(random_state=int(seed),**GBR_PARAMS)
        elif kind=='HGBR':
            self.model=HistGradientBoostingRegressor(random_state=int(seed),**PUBLIC_HGBR_PARAMS)
        else: raise ValueError(kind)
        self.scores=None; self.q=None
    def fit(self,Xtr,ytr,Xcal,ycal):
        self.model.fit(Xtr,ytr)
        self.scores=np.abs(np.asarray(ycal)-self.model.predict(Xcal))
        self.q=conformal_quantile(self.scores,ALPHA)
        return self
    def predict_scp(self,X):
        p=self.model.predict(X); return p-self.q,p+self.q
    def predict_wcp(self,X,wcal,wtest):
        order=np.argsort(self.scores); s=self.scores[order]; w=np.asarray(wcal,float)[order]
        cw=np.cumsum(w); target=(1-ALPHA)*(float(cw[-1])+np.asarray(wtest,float))
        idx=np.searchsorted(cw,target,side='left'); q=np.full(len(np.asarray(wtest)),np.inf)
        ok=idx<len(s); q[ok]=s[idx[ok]]
        p=self.model.predict(X); return p-q,p+q

class CQRLinear:
    def __init__(self):
        self.lo=QuantileRegressor(quantile=ALPHA/2,alpha=CQR_LINEAR_ALPHA,solver='highs')
        self.hi=QuantileRegressor(quantile=1-ALPHA/2,alpha=CQR_LINEAR_ALPHA,solver='highs')
        self.q=None
    def fit(self,Xtr,ytr,Xcal,ycal):
        self.lo.fit(Xtr,ytr); self.hi.fit(Xtr,ytr)
        lo=self.lo.predict(Xcal); hi=self.hi.predict(Xcal)
        self.q=conformal_quantile(np.maximum(lo-np.asarray(ycal),np.asarray(ycal)-hi),ALPHA)
        return self
    def predict(self,X):
        return self.lo.predict(X)-self.q,self.hi.predict(X)+self.q

def rec(rows,base,method,lo,hi,metrics):
    rows.append({**base,'method':method,**metrics})

def path_areas(df,groups):
    outs=[]
    for key,g in df.groupby(groups+['method'],dropna=False):
        key=key if isinstance(key,tuple) else (key,); g=g.sort_values('severity'); x=g.severity.to_numpy(float)
        r={c:v for c,v in zip(groups+['method'],key)}
        for col,name in [('coverage_deficit','A_cov'),('coverage_gap','A_gap'),('mean_width_finite','A_width'),('interval_score_finite','A_score'),('infinite_interval_fraction','A_inf')]:
            y=g[col].to_numpy(float)
            r[name]=float(np.trapezoid(y,x)) if np.isfinite(y).all() else np.nan
        outs.append(r)
    return pd.DataFrame(outs)

def run_synthetic(rep_start=0,rep_end=None):
    cfg=yaml.safe_load((SYN/'configs/main_v10_locked.yaml').read_text()); master=int(cfg['seed']); p=int(cfg['n_features'])
    end=int(cfg['repetitions']) if rep_end is None else min(int(rep_end),int(cfg['repetitions']))
    rows=[]
    for rep in range(int(rep_start),end):
      for di,dgp in enumerate(cfg['dgp_types']):
       for ni,noise in enumerate(cfg['noise_types']):
        sseed=derived_seed(master,rep,di,ni,100); mseed=derived_seed(master,rep,di,ni,200)
        Xtr,ytr,Xcal,ycal=generate_source_split(np.random.default_rng(sseed),int(cfg['n_train']),int(cfg['n_cal']),p,dgp,noise)
        ridge=MeanConformal('Ridge',mseed).fit(Xtr,ytr,Xcal,ycal)
        gbr=MeanConformal('GBR',mseed).fit(Xtr,ytr,Xcal,ycal)
        cqr_gbr=ConformalizedQuantileRegressor(alpha=ALPHA,n_estimators=int(cfg['cqr_estimators']),random_state=mseed).fit(Xtr,ytr,Xcal,ycal)
        cqr_lin=CQRLinear().fit(Xtr,ytr,Xcal,ycal)
        bXt,byt=generate_target(np.random.default_rng(derived_seed(master,rep,di,ni,0,0,302)),int(cfg['n_test']),p,cfg['shift_families'][0],0.,dgp,noise)
        for fi,fam in enumerate(cfg['shift_families']):
          for si,sv in enumerate(cfg['severities']):
            sev=float(sv)
            if sev==0: Xt,yt=bXt,byt
            else: Xt,yt=generate_target(np.random.default_rng(derived_seed(master,rep,di,ni,fi,si,302)),int(cfg['n_test']),p,fam,sev,dgp,noise)
            base={'layer':'synthetic','rep':rep,'dgp':dgp,'noise':noise,'scenario':fam,'severity':sev}
            for name,obj in [('SCP-Ridge',ridge),('SCP-GBR',gbr)]:
                lo,hi=obj.predict_scp(Xt); rec(rows,base,name,lo,hi,syn_metrics(yt,lo,hi,ALPHA))
            lo,hi=cqr_gbr.predict_interval(Xt); rec(rows,base,'CQR-GBR',lo,hi,syn_metrics(yt,lo,hi,ALPHA))
            lo,hi=cqr_lin.predict(Xt); rec(rows,base,'CQR-Linear',lo,hi,syn_metrics(yt,lo,hi,ALPHA))
            wc=oracle_density_ratio(Xcal,fam,sev); wt=oracle_density_ratio(Xt,fam,sev)
            if wc is not None and wt is not None:
                for name,obj in [('Oracle-WCP-Ridge',ridge),('Oracle-WCP-GBR',gbr)]:
                    lo,hi=obj.predict_wcp(Xt,wc,wt); rec(rows,base,name,lo,hi,syn_metrics(yt,lo,hi,ALPHA))
        print(f'P04 synth rep={rep} dgp={dgp} noise={noise}',flush=True)
    return pd.DataFrame(rows)

def run_public(rep_start=0,rep_end=None,datasets=None,modes=('directional','radial')):
    cfg=json.loads((REAL/'configs/real_data_prelock.json').read_text()); master=int(cfg['master_seed']); order=['ccpp','appliances','superconductivity','gas_turbine_nox','online_news']; datasets=order if datasets is None else datasets
    end=int(cfg['repetitions']) if rep_end is None else min(int(rep_end),int(cfg['repetitions'])); rows=[]
    for key in datasets:
      didx=order.index(key); df=pd.read_csv(DATA[key]); X=df.drop(columns=['target']).to_numpy(float); y=df.target.to_numpy(float); n=len(X)
      for rep in range(int(rep_start),end):
        split_seed=derive_seed(master,didx,rep,0,10); it,ic,ir=paired_split_indices(n,split_seed,float(cfg['split_fractions']['train']),float(cfg['split_fractions']['calibration']))
        Xtr,ytr=X[it],y[it]; Xcal,ycal=X[ic],y[ic]; Xres,yres=X[ir],y[ir]
        xsc=StandardScaler().fit(Xtr); Xtr_s=xsc.transform(Xtr); Xcal_s=xsc.transform(Xcal)
        ymu=float(ytr.mean()); ysd=float(ytr.std(ddof=0)); ysd=ysd if ysd>0 else 1.0; ytr_s=(ytr-ymu)/ysd; ycal_s=(ycal-ymu)/ysd
        seed=derive_seed(master,didx,rep,0,20); ridge=MeanConformal('Ridge',seed).fit(Xtr_s,ytr_s,Xcal_s,ycal_s); gbr=MeanConformal('HGBR',seed).fit(Xtr_s,ytr_s,Xcal_s,ycal_s)
        for mode in modes:
            if mode=='directional': basis=fit_directional_basis(Xtr,float(cfg['score_clip'])); score=lambda A:basis.score(A); sevs=cfg['directional_tilt_lambda']
            elif mode=='radial': basis=fit_radial_basis(Xtr,float(cfg['score_clip'])); score=lambda A:radial_score(A,basis); sevs=cfg['radial_sensitivity_lambda']
            else: raise ValueError(mode)
            for si,sv in enumerate(sevs):
                sev=float(sv); probs=tilt_sampling_probabilities(score(Xres),sev); ix,_=sample_target_indices(len(Xres),probs,int(cfg['target_test_n']),derive_seed(master,didx,rep,si,50)); Xt=Xres[ix]; yt=yres[ix]; Xt_s=xsc.transform(Xt); yt_s=(yt-ymu)/ysd
                base={'layer':'public','dataset':key,'rep':rep,'scenario':mode,'severity':sev}
                for name,obj in [('SCP-Ridge',ridge),('SCP-HGBR',gbr)]:
                    lo,hi=obj.predict_scp(Xt_s); rec(rows,base,name,lo,hi,real_metrics(yt_s,lo,hi,ALPHA))
                wc=tilt_ratio(score(Xcal),sev); wt=tilt_ratio(score(Xt),sev)
                for name,obj in [('Known-tilt-WCP-Ridge',ridge),('Known-tilt-WCP-HGBR',gbr)]:
                    lo,hi=obj.predict_wcp(Xt_s,wc,wt); rec(rows,base,name,lo,hi,real_metrics(yt_s,lo,hi,ALPHA))
        print(f'P04 public dataset={key} rep={rep}',flush=True)
    return pd.DataFrame(rows)

def paired_ci(d):
    d=np.asarray(d,float); d=d[np.isfinite(d)]; n=len(d); m=float(d.mean()) if n else np.nan
    if n>1:
        se=float(d.std(ddof=1)/math.sqrt(n)); c=float(t.ppf(.975,n-1)); return n,m,m-c*se,m+c*se
    return n,m,np.nan,np.nan

def factorial_contrasts(areas,layer):
    rows=[]
    group_cols=['dgp','noise','scenario'] if layer=='synthetic' else ['dataset','scenario']
    for key,g in areas.groupby(group_cols,dropna=False):
        key=key if isinstance(key,tuple) else (key,); meta=dict(zip(group_cols,key)); piv=g.pivot(index='rep',columns='method',values=['A_cov','A_gap','A_width'])
        if layer=='synthetic': wr, wg='Oracle-WCP-Ridge','Oracle-WCP-GBR'
        else: wr,wg='Known-tilt-WCP-Ridge','Known-tilt-WCP-HGBR'
        for metric in ['A_cov','A_gap','A_width']:
            P=piv[metric]
            specs=[('Backbone effect within SCP',('SCP-GBR' if layer=='synthetic' else 'SCP-HGBR'),'SCP-Ridge'),('Backbone effect within WCP',wg,wr),('Wrapper effect within Ridge',wr,'SCP-Ridge'),('Wrapper effect within second backbone',wg,('SCP-GBR' if layer=='synthetic' else 'SCP-HGBR'))]
            for label,a,b in specs:
                if a in P and b in P:
                    n,m,lo,hi=paired_ci((P[a]-P[b]).dropna()); rows.append({'layer':layer,**meta,'metric':metric,'contrast':label,'n':n,'mean_difference':m,'ci95_low':lo,'ci95_high':hi})
            second_scp=('SCP-GBR' if layer=='synthetic' else 'SCP-HGBR')
            if all(x in P for x in [wg,second_scp,wr,'SCP-Ridge']):
                d=(P[wg]-P[second_scp])-(P[wr]-P['SCP-Ridge']); n,m,lo,hi=paired_ci(d.dropna()); rows.append({'layer':layer,**meta,'metric':metric,'contrast':'Wrapper x backbone interaction','n':n,'mean_difference':m,'ci95_low':lo,'ci95_high':hi})
        if layer=='synthetic' and 'CQR-GBR' in piv['A_cov'] and 'CQR-Linear' in piv['A_cov']:
            for metric in ['A_cov','A_gap','A_width']:
                P=piv[metric]; n,m,lo,hi=paired_ci((P['CQR-GBR']-P['CQR-Linear']).dropna()); rows.append({'layer':layer,**meta,'metric':metric,'contrast':'CQR model-family effect (GBR - Linear)','n':n,'mean_difference':m,'ci95_low':lo,'ci95_high':hi})
    return pd.DataFrame(rows)

def summarize(syn,pub,out):
    out.mkdir(parents=True,exist_ok=True); syn.to_csv(out/'raw_p04_synthetic.csv',index=False); pub.to_csv(out/'raw_p04_public.csv',index=False)
    asyn=path_areas(syn,['rep','dgp','noise','scenario']); apub=path_areas(pub,['dataset','rep','scenario']); asyn.to_csv(out/'path_areas_p04_synthetic.csv',index=False); apub.to_csv(out/'path_areas_p04_public.csv',index=False)
    cs=factorial_contrasts(asyn[asyn.scenario!='nonlinear'],'synthetic'); cp=factorial_contrasts(apub,'public'); pd.concat([cs,cp],ignore_index=True).to_csv(out/'factorial_contrasts_p04.csv',index=False)
    ss=asyn.groupby(['dgp','noise','scenario','method'],as_index=False).agg(A_cov=('A_cov','mean'),A_gap=('A_gap','mean'),A_width=('A_width','mean'),A_inf=('A_inf','mean')); ps=apub.groupby(['dataset','scenario','method'],as_index=False).agg(A_cov=('A_cov','mean'),A_gap=('A_gap','mean'),A_width=('A_width','mean'),A_inf=('A_inf','mean')); ss.to_csv(out/'area_summary_p04_synthetic.csv',index=False); ps.to_csv(out/'area_summary_p04_public.csv',index=False)
    # interaction summary counts: CI excludes zero / includes zero by metric
    fc=pd.concat([cs,cp],ignore_index=True); inter=fc[fc.contrast=='Wrapper x backbone interaction'].copy(); inter['class']=np.where(inter.ci95_low>0,'positive',np.where(inter.ci95_high<0,'negative','includes_zero')); inter.groupby(['layer','metric','class']).size().rename('count').reset_index().to_csv(out/'interaction_ci_counts_p04.csv',index=False)
    qa={'synthetic_rows':len(syn),'public_rows':len(pub),'synthetic_reps':int(syn.rep.nunique()),'public_reps':int(pub.rep.nunique()),'public_datasets':sorted(pub.dataset.unique().tolist()),'duplicate_synthetic_keys':int(syn.duplicated(['rep','dgp','noise','scenario','severity','method']).sum()),'duplicate_public_keys':int(pub.duplicated(['dataset','rep','scenario','severity','method']).sum()),'coverage_outside_0_1':int((((pd.concat([syn,pub]).coverage)<0)|((pd.concat([syn,pub]).coverage)>1)).sum())}
    (out/'qa_p04.json').write_text(json.dumps(qa,indent=2))
    manifest={'version':'P0-4-v1','purpose':'common-backbone factorial separation of wrapper and predictor effects','factorial_core':{'wrappers':['SCP','known-weight WCP'],'synthetic_backbones':['Ridge(alpha=1)','mean GBR'],'public_backbones':['Ridge(alpha=1)','HistGradientBoostingRegressor'],'interaction':'(WCP_GBR-SCP_GBR)-(WCP_Ridge-SCP_Ridge)'},'synthetic_gbr':GBR_PARAMS,'public_hgbr':PUBLIC_HGBR_PARAMS,'cqr_family_sensitivity':{'synthetic_only':True,'CQR-GBR':'locked 0.05/0.95 gradient boosted quantiles, 80 estimators','CQR-Linear':f'QuantileRegressor q=.05/.95 alpha={CQR_LINEAR_ALPHA}, solver=highs'},'synthetic':{'repetitions':int(syn.rep.nunique()),'all_dgp_noise':True,'all_shift_families':True,'factorial_oracle_families':['mean','variance','mixture','tail_mixture']},'public':{'repetitions':int(pub.rep.nunique()),'datasets':sorted(pub.dataset.unique().tolist()),'modes':sorted(pub.scenario.unique().tolist()),'target_test_n':2500},'data_sha256':{k:sha256(v) for k,v in DATA.items()}}
    (out/'manifest_p04.json').write_text(json.dumps(manifest,indent=2))
    checks=[]
    for p in sorted(out.iterdir()):
        if p.is_file() and p.name!='checksums_p04.json': checks.append({'file':p.name,'sha256':sha256(p),'bytes':p.stat().st_size})
    (out/'checksums_p04.json').write_text(json.dumps(checks,indent=2))
    print('QA',json.dumps(qa,indent=2)); print('INTERACTION COUNTS\n',pd.read_csv(out/'interaction_ci_counts_p04.csv').to_string(index=False))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--smoke',action='store_true'); ap.add_argument('--syn-start',type=int,default=0); ap.add_argument('--syn-end',type=int); ap.add_argument('--pub-start',type=int,default=0); ap.add_argument('--pub-end',type=int); ap.add_argument('--datasets',nargs='*'); ap.add_argument('--out',default=str(HERE/'results_rerun'))
    a=ap.parse_args(); t0=time.time()
    if a.smoke:
        syn=run_synthetic(0,1); pub=run_public(0,1,['ccpp'])
    else:
        syn=run_synthetic(a.syn_start,a.syn_end); pub=run_public(a.pub_start,a.pub_end,a.datasets)
    summarize(syn,pub,Path(a.out)); print('seconds',time.time()-t0)
if __name__=='__main__': main()
