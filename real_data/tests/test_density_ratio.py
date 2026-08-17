import numpy as np
from density_ratio import fit_density_ratio, heldout_domain_auc

def test_ratio_positive_finite_and_batch_invariant():
    rng=np.random.default_rng(4)
    xs=rng.normal(size=(500,12)); xt=rng.normal(size=(500,12)); xt[:,0]+=0.5
    m=fit_density_ratio(xs,xt,C=0.1)
    q=rng.normal(size=(800,12)); w=m.ratio(q)
    assert np.isfinite(w).all() and (w>0).all()
    x=q[:1]
    assert np.isclose(m.ratio(x)[0],m.ratio(np.vstack([x,q[1:20]]))[0])

def test_null_auc_near_half():
    rng=np.random.default_rng(9)
    xs=rng.normal(size=(2000,8)); xt=rng.normal(size=(2000,8))
    m=fit_density_ratio(xs[:1000],xt[:1000],C=0.1)
    auc=heldout_domain_auc(m,xs[1000:],xt[1000:])
    assert 0.44 < auc < 0.56

def test_shift_auc_above_half():
    rng=np.random.default_rng(12)
    xs=rng.normal(size=(2000,6)); xt=rng.normal(size=(2000,6)); xt[:,0]+=1.0
    m=fit_density_ratio(xs[:1000],xt[:1000],C=0.1)
    auc=heldout_domain_auc(m,xs[1000:],xt[1000:])
    assert auc>0.65
