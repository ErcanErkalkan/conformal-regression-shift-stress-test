import json
from pathlib import Path
import numpy as np, pandas as pd
from run_real_benchmark import run_dataset, merge

def test_mock_directional_runner_and_merge(tmp_path):
    rng=np.random.default_rng(123)
    n=1800; p=4
    X=rng.normal(size=(n,p)); y=1.5*X[:,0]-X[:,1]+0.3*X[:,2]**2+rng.normal(scale=.7,size=n)
    data=tmp_path/'data'; data.mkdir(); pd.DataFrame(np.c_[X,y],columns=[f'x{i}' for i in range(p)]+['target']).to_csv(data/'mock.csv',index=False)
    cfg={
      'protocol_version':'test','master_seed':77,'repetitions':2,
      'split_fractions':{'train':.4,'calibration':.25,'reservoir':.35},
      'directional_tilt_lambda':[0.,.5,1.], 'radial_sensitivity_lambda':[0.,1.],
      'score_clip':3.,'target_unlabeled_n':100,'target_test_n':200,
      'nominal_coverage':.9,'coverage_lower_bound':.87,'persistence':2,
      'info_ess_ratio_threshold':.2,'infinite_fraction_threshold':.05,
      'primary_density_ratio':{'model':'linear_logistic','logistic_C':.1},
      'sensitivity_density_ratio':{'model':'linear_logistic','logistic_C':.01},
      'density_source_n':100,'cqr_estimators':10}
    run=tmp_path/'shards'
    run_dataset(cfg,'mock',0,data,run,0,1,'directional')
    run_dataset(cfg,'mock',0,data,run,1,2,'directional')
    out=tmp_path/'merged'; merge(cfg,run,out)
    raw=pd.read_csv(out/'raw_results_real_v03.csv')
    assert len(raw)==2*3*5
    assert raw[['coverage','coverage_gap','coverage_deficit']].notna().all().all()
    assert (out/'breakpoints_real_v03.csv').exists()
    assert (out/'paired_method_differences_real_v03.csv').exists()
