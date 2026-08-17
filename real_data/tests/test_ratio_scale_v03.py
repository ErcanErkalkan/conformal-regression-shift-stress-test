import numpy as np
from density_ratio import fit_density_ratio
from shift_design import tilt_ratio, tilt_sampling_probabilities

def test_oracle_ratio_common_scale_not_batch_normalized():
    a=np.array([-1.,0.,1.]); b=np.array([1.,2.])
    wa=tilt_ratio(a,1.0); wb=tilt_ratio(b,1.0)
    assert np.isclose(wa[-1], wb[0])
    assert not np.isclose(wa.mean(),1.0)
    p=tilt_sampling_probabilities(a,1.0)
    assert np.isclose(p.sum(),1.0)

def test_estimated_ratio_same_point_same_weight_across_batches():
    rng=np.random.default_rng(4)
    xs=rng.normal(size=(200,3)); xt=rng.normal(loc=.5,size=(200,3))
    m=fit_density_ratio(xs,xt,C=.1)
    x=np.array([[.2,-.1,.4]])
    r1=m.ratio(x)[0]
    r2=m.ratio(np.vstack([x, [[2.,2.,2.]]]))[0]
    assert np.isclose(r1,r2)
