from __future__ import annotations
import argparse, hashlib, json, platform, sys, time
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import t

from shift_design import (
    fit_directional_basis, fit_radial_basis, radial_score, paired_split_indices,
    sample_target_indices, derive_seed, tilt_ratio, tilt_sampling_probabilities,
)
from density_ratio import fit_density_ratio, heldout_domain_auc
from real_methods import ScaledRealMethods
from metrics_core import interval_metrics, weight_diagnostics, normalized_weight_error, rbf_mmd2
from metrics_v10 import metric_rank_reversals, persistent_threshold_breakpoint

VERSION = "0.3-prelock-runner"


def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()


def config_hash(cfg: dict) -> str:
    return hashlib.sha256(json.dumps(cfg,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def load_canonical(data_dir: Path, key: str):
    p=data_dir/f"{key}.csv"
    if not p.exists(): raise FileNotFoundError(f"Missing canonical dataset: {p}")
    df=pd.read_csv(p)
    if 'target' not in df.columns: raise ValueError(f"{key}: canonical target column missing")
    X=df.drop(columns=['target']).to_numpy(float); y=df['target'].to_numpy(float)
    if not np.all(np.isfinite(X)) or not np.all(np.isfinite(y)): raise ValueError(f"{key}: non-finite data")
    return X,y,p


def _record(rows, base, method, auc, mmd2, diag, met, unique_u, unique_t, werr=None):
    d={**base,'method':method,'shift_classifier_auc':auc,'mmd2':mmd2,
       'target_unlabeled_unique_fraction':unique_u,'target_test_unique_fraction':unique_t,
       **diag,**met}
    if werr: d.update(werr)
    rows.append(d)


def aggregate(raw: pd.DataFrame, cfg: dict, out: Path):
    reps=int(cfg['repetitions']); alpha=1-float(cfg['nominal_coverage'])
    grp=['dataset','shift_mode','severity','method']
    agg=raw.groupby(grp,as_index=False).agg(
        coverage_mean=('coverage','mean'),coverage_sd=('coverage','std'),
        coverage_gap_mean=('coverage_gap','mean'),coverage_deficit_mean=('coverage_deficit','mean'),
        width_mean=('mean_width_finite','mean'),interval_score_mean=('interval_score_finite','mean'),
        infinite_fraction_mean=('infinite_interval_fraction','mean'),
        ess_ratio_mean=('ess_ratio','mean'),weight_cv_mean=('weight_cv','mean'),
        max_normalized_weight_mean=('max_normalized_weight','mean'),shift_auc_mean=('shift_classifier_auc','mean'),
        mmd2_mean=('mmd2','mean'),log_weight_rmse_mean=('log_weight_rmse','mean'),
        log_weight_mae_mean=('log_weight_mae','mean'),log_weight_corr_mean=('log_weight_corr','mean'),
        target_unlabeled_unique_fraction_mean=('target_unlabeled_unique_fraction','mean'),
        target_test_unique_fraction_mean=('target_test_unique_fraction','mean'))
    agg['n_reps']=raw.groupby(grp).size().to_numpy()
    agg['coverage_se']=agg['coverage_sd']/np.sqrt(agg['n_reps'])
    crit=agg['n_reps'].apply(lambda n: t.ppf(.975,max(int(n)-1,1)) if n>1 else np.nan)
    agg['coverage_ci95_low']=np.clip(agg['coverage_mean']-crit*agg['coverage_se'],0,1)
    agg['coverage_ci95_high']=np.clip(agg['coverage_mean']+crit*agg['coverage_se'],0,1)
    agg.to_csv(out/'summary_real_v03.csv',index=False)

    lower=float(cfg['coverage_lower_bound']); p=int(cfg['persistence'])
    gcols=['dataset','shift_mode','method']
    base=agg[agg.severity==0][gcols+['coverage_mean','coverage_ci95_high','ess_ratio_mean','infinite_fraction_mean']].copy()
    base['baseline_undercoverage']=base.coverage_mean<lower
    base['baseline_undercoverage_CI']=base.coverage_ci95_high<lower
    base['baseline_info_fragile']=base.ess_ratio_mean<=float(cfg['info_ess_ratio_threshold'])
    base['baseline_usability_issue']=base.infinite_fraction_mean>=float(cfg['infinite_fraction_threshold'])
    base.to_csv(out/'baseline_quality_real_v03.csv',index=False)

    shifted=agg[agg.severity>0].copy()
    bc=persistent_threshold_breakpoint(shifted,gcols,'coverage_mean',lower,'lt',p,'B_cov')
    bci=persistent_threshold_breakpoint(shifted,gcols,'coverage_ci95_high',lower,'lt',p,'B_cov_CI')
    bi=persistent_threshold_breakpoint(shifted,gcols,'ess_ratio_mean',float(cfg['info_ess_ratio_threshold']),'le',p,'B_info')
    bf=persistent_threshold_breakpoint(shifted,gcols,'infinite_fraction_mean',float(cfg['infinite_fraction_threshold']),'ge',p,'B_inf')
    bp=bc.merge(bci,on=gcols,how='outer').merge(bi,on=gcols,how='outer').merge(bf,on=gcols,how='outer')
    bp.to_csv(out/'breakpoints_real_v03.csv',index=False)

    rank_frames=[]
    common=['SCP-Ridge','CQR-GBR','Estimated-WCP-Primary','Oracle-WCP-Ridge']
    for dataset,gd in agg.groupby('dataset'):
        x=gd.copy(); x['shift_family']=x['shift_mode']
        for metric in ['coverage_deficit_mean','coverage_gap_mean','infinite_fraction_mean']:
            rr=metric_rank_reversals(x,['dataset','shift_mode'],common,metric)
            if not rr.empty: rank_frames.append(rr)
        rr=metric_rank_reversals(x,['dataset','shift_mode'],common,'interval_score_mean',require_all_zero_infinite=True)
        if not rr.empty: rank_frames.append(rr)
    if rank_frames: pd.concat(rank_frames,ignore_index=True).to_csv(out/'rank_reversals_real_v03.csv',index=False)

    # Per-repetition trajectory integrals on the native lambda axis.
    traj_rows=[]
    for key,g in raw.groupby(['dataset','rep','shift_mode','method'],dropna=False):
        g=g.sort_values('severity'); x=g['severity'].to_numpy(float)
        if len(np.unique(x))<2: continue
        row=dict(zip(['dataset','rep','shift_mode','method'],key))
        for col,name in [('coverage_deficit','auc_coverage_deficit'),('coverage_gap','auc_coverage_gap'),('infinite_interval_fraction','auc_infinite_fraction')]:
            y=g[col].to_numpy(float); row[name]=float(np.trapezoid(y,x)) if np.all(np.isfinite(y)) else np.nan
        y=g['ess_ratio'].to_numpy(float); row['auc_information_loss']=float(np.trapezoid(1-y,x)) if np.all(np.isfinite(y)) else np.nan
        traj_rows.append(row)
    pd.DataFrame(traj_rows).to_csv(out/'trajectory_metrics_real_v03.csv',index=False)

    # Paired method differences over identical repetitions and target draws.
    pair_rows=[]
    def pair_ci(a,b,value,label):
        keys=['dataset','shift_mode','severity','rep']
        pa=raw[raw.method==a][keys+[value]].rename(columns={value:'a'})
        pb=raw[raw.method==b][keys+[value]].rename(columns={value:'b'})
        m=pa.merge(pb,on=keys)
        for k,g in m.groupby(['dataset','shift_mode','severity'],dropna=False):
            dif=(g.a-g.b).to_numpy(float); dif=dif[np.isfinite(dif)]; n=len(dif)
            if not n: continue
            mean=float(dif.mean()); sd=float(dif.std(ddof=1)) if n>1 else np.nan
            se=sd/np.sqrt(n) if n>1 else np.nan; crit=float(t.ppf(.975,n-1)) if n>1 else np.nan
            pair_rows.append({'dataset':k[0],'shift_mode':k[1],'severity':k[2],'comparison':label,'metric':value,'n':n,'mean_difference':mean,'ci95_low':mean-crit*se if n>1 else np.nan,'ci95_high':mean+crit*se if n>1 else np.nan})
    for metric in ['coverage','coverage_deficit','infinite_interval_fraction','interval_score_finite','ess_ratio']:
        pair_ci('Estimated-WCP-Primary','Oracle-WCP-Ridge',metric,'Primary - Oracle')
        pair_ci('Estimated-WCP-Sensitivity','Oracle-WCP-Ridge',metric,'Sensitivity - Oracle')
        pair_ci('Estimated-WCP-Primary','Estimated-WCP-Sensitivity',metric,'Primary - Sensitivity')
        pair_ci('Estimated-WCP-Primary','SCP-Ridge',metric,'Primary - SCP')
    pd.DataFrame(pair_rows).to_csv(out/'paired_method_differences_real_v03.csv',index=False)


def run_dataset(cfg:dict,key:str,dataset_index:int,data_dir:Path,out:Path,rep_start:int,rep_end:int,shift_mode='directional'):
    X,y,path=load_canonical(data_dir,key)
    n=len(X); rows=[]; seeds=[]
    train_frac=float(cfg['split_fractions']['train']); cal_frac=float(cfg['split_fractions']['calibration'])
    severities=cfg['directional_tilt_lambda'] if shift_mode=='directional' else cfg['radial_sensitivity_lambda']
    master=int(cfg['master_seed']); density_n=int(cfg['density_source_n'])
    for rep in range(rep_start,rep_end):
        split_seed=derive_seed(master,dataset_index,rep,0,10)
        it,ic,ir=paired_split_indices(n,split_seed,train_frac,cal_frac)
        Xtr,ytr=X[it],y[it]; Xcal,ycal=X[ic],y[ic]; Xres,yres=X[ir],y[ir]
        model_seed=derive_seed(master,dataset_index,rep,0,20)
        methods=ScaledRealMethods(alpha=1-float(cfg['nominal_coverage']),cqr_estimators=int(cfg.get('cqr_estimators',80)),random_state=model_seed).fit(Xtr,ytr,Xcal,ycal)
        if shift_mode=='directional':
            basis=fit_directional_basis(Xtr,float(cfg['score_clip']))
            score=lambda A:basis.score(A)
        elif shift_mode=='radial':
            basis=fit_radial_basis(Xtr,float(cfg['score_clip']))
            score=lambda A:radial_score(A,basis)
        else: raise ValueError(shift_mode)

        dens_seed=derive_seed(master,dataset_index,rep,0,30)
        drng=np.random.default_rng(dens_seed)
        if len(Xtr)<density_n: raise ValueError(f"{key}: train split smaller than density_source_n")
        dens_idx=drng.choice(len(Xtr),size=density_n,replace=False)
        Xdens=Xtr[dens_idx]

        for si,sev in enumerate(map(float,severities)):
            probs=tilt_sampling_probabilities(score(Xres),sev)
            useed=derive_seed(master,dataset_index,rep,si,40)
            tseed=derive_seed(master,dataset_index,rep,si,50)
            iu,uf=sample_target_indices(len(Xres),probs,int(cfg['target_unlabeled_n']),useed)
            ix,tf=sample_target_indices(len(Xres),probs,int(cfg['target_test_n']),tseed)
            Xu=Xres[iu]; Xt=Xres[ix]; yt=yres[ix]
            Xt_s,yt_s=methods.xy_test(Xt,yt)
            Xtr_s=methods.x_scaler.transform(Xtr); Xu_s=methods.x_scaler.transform(Xu)
            mmd=rbf_mmd2(Xtr_s,Xu_s,max_points=250)
            base={'dataset':key,'rep':rep,'shift_mode':shift_mode,'severity':sev}
            diag0={'ess':len(Xcal),'ess_ratio':1.0,'weight_cv':0.0,'max_normalized_weight':1/len(Xcal)}
            lo,hi=methods.scp.predict_interval(Xt_s)
            _record(rows,base,'SCP-Ridge',np.nan,mmd,diag0,interval_metrics(yt_s,lo,hi,1-float(cfg['nominal_coverage'])),uf,tf)
            lo,hi=methods.cqr.predict_interval(Xt_s)
            _record(rows,base,'CQR-GBR',np.nan,mmd,diag0,interval_metrics(yt_s,lo,hi,1-float(cfg['nominal_coverage'])),uf,tf)

            wo_cal=tilt_ratio(score(Xcal),sev); wo_test=tilt_ratio(score(Xt),sev)
            for label,C,stream in [
                ('Estimated-WCP-Primary',float(cfg['primary_density_ratio']['logistic_C']),60),
                ('Estimated-WCP-Sensitivity',float(cfg['sensitivity_density_ratio']['logistic_C']),70)]:
                est=fit_density_ratio(Xdens,Xu,C=C)
                auc=heldout_domain_auc(est,Xcal,Xt)
                we_cal=est.ratio(Xcal); we_test=est.ratio(Xt)
                diag=weight_diagnostics(we_cal); werr=normalized_weight_error(we_cal,wo_cal)
                lo,hi=methods.wcp.predict_interval_weighted(Xt_s,we_cal,we_test)
                _record(rows,base,label,auc,mmd,diag,interval_metrics(yt_s,lo,hi,1-float(cfg['nominal_coverage'])),uf,tf,werr)
            diag=weight_diagnostics(wo_cal)
            lo,hi=methods.wcp.predict_interval_weighted(Xt_s,wo_cal,wo_test)
            _record(rows,base,'Oracle-WCP-Ridge',np.nan,mmd,diag,interval_metrics(yt_s,lo,hi,1-float(cfg['nominal_coverage'])),uf,tf,{'log_weight_rmse':0.0,'log_weight_mae':0.0,'log_weight_corr':1.0,'estimated_to_oracle_ess_ratio':1.0})
            seeds.append({'dataset':key,'rep':rep,'shift_mode':shift_mode,'severity':sev,'split_seed':split_seed,'model_seed':model_seed,'density_source_seed':dens_seed,'target_unlabeled_seed':useed,'target_test_seed':tseed})
    out.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(rows).to_csv(out/f'raw_{key}_{shift_mode}_{rep_start:02d}_{rep_end:02d}.csv',index=False)
    pd.DataFrame(seeds).to_csv(out/f'seeds_{key}_{shift_mode}_{rep_start:02d}_{rep_end:02d}.csv',index=False)
    meta={'version':VERSION,'dataset':key,'shift_mode':shift_mode,'rep_start':rep_start,'rep_end':rep_end,'config_hash':config_hash(cfg),'canonical_sha256':sha256_file(path),'rows':len(rows),'seed_rows':len(seeds)}
    (out/f'manifest_{key}_{shift_mode}_{rep_start:02d}_{rep_end:02d}.json').write_text(json.dumps(meta,indent=2))
    return meta


def merge(cfg:dict,run_dir:Path,out:Path):
    files=sorted(run_dir.glob('raw_*.csv'))
    if not files: raise FileNotFoundError('No raw shard files')
    raw=pd.concat([pd.read_csv(p) for p in files],ignore_index=True)
    keycols=['dataset','rep','shift_mode','severity','method']
    if raw.duplicated(keycols).any(): raise ValueError('Duplicate result keys in merge')
    expected_datasets=sorted([x['key'] for x in json.loads(Path(cfg['dataset_manifest_path']).read_text())['datasets']]) if 'dataset_manifest_path' in cfg else sorted(raw.dataset.unique())
    # validate primary directional result size only if all expected datasets are present
    if set(expected_datasets).issubset(set(raw.dataset.unique())) and set(raw.shift_mode.unique())=={'directional'}:
        expected=len(expected_datasets)*int(cfg['repetitions'])*len(cfg['directional_tilt_lambda'])*5
        if len(raw)!=expected: raise ValueError(f'Expected {expected} result rows, got {len(raw)}')
    seedfiles=sorted(run_dir.glob('seeds_*.csv')); seeds=pd.concat([pd.read_csv(p) for p in seedfiles],ignore_index=True)
    if seeds.duplicated(['dataset','rep','shift_mode','severity']).any(): raise ValueError('Duplicate seed keys')
    out.mkdir(parents=True,exist_ok=True)
    raw.to_csv(out/'raw_results_real_v03.csv',index=False); seeds.to_csv(out/'seed_manifest_real_v03.csv',index=False)
    aggregate(raw,cfg,out)
    (out/'merge_manifest_real_v03.json').write_text(json.dumps({'version':VERSION,'rows':len(raw),'seed_rows':len(seeds),'config_hash':config_hash(cfg)},indent=2))


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--config',default='configs/real_data_prelock.json'); ap.add_argument('--data-dir',default='data/canonical'); ap.add_argument('--out',default='runs/real_v03'); ap.add_argument('--dataset'); ap.add_argument('--dataset-index',type=int,default=0); ap.add_argument('--rep-start',type=int,default=0); ap.add_argument('--rep-end',type=int); ap.add_argument('--shift-mode',choices=['directional','radial'],default='directional'); ap.add_argument('--merge',action='store_true'); ap.add_argument('--run-dir')
    a=ap.parse_args(); cfg=json.loads(Path(a.config).read_text()); cfg['dataset_manifest_path']=str(Path(a.config).parent/'dataset_manifest.json')
    if a.merge:
        merge(cfg,Path(a.run_dir or a.out),Path(a.out)); return
    if not a.dataset: raise SystemExit('--dataset required unless --merge')
    end=int(cfg['repetitions']) if a.rep_end is None else int(a.rep_end)
    print(run_dataset(cfg,a.dataset,a.dataset_index,Path(a.data_dir),Path(a.out),int(a.rep_start),end,a.shift_mode))

if __name__=='__main__': main()
