import numpy as np
from shift_design import (
    fit_directional_basis, fit_radial_basis, radial_score,
    normalized_tilt_weights, ess_ratio, paired_split_indices,
    sample_target_indices, derive_seed
)


def make_data(seed=1, n=1000, p=6):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n,p))
    X[:,1] = 0.7*X[:,0] + np.sqrt(1-0.7**2)*X[:,1]
    return X


def test_lambda_zero_uniform_weights():
    s=np.linspace(-3,3,101)
    w=normalized_tilt_weights(s,0.0)
    assert np.allclose(w,1.0)
    assert np.isclose(ess_ratio(w),1.0)


def test_directional_score_bounded_and_standardized():
    X=make_data()
    b=fit_directional_basis(X,clip=3.0)
    s=b.score(X)
    assert np.max(np.abs(s)) <= 3.0 + 1e-12
    assert abs(np.mean(s)) < 0.02
    assert 0.90 < np.std(s) < 1.02


def test_pc1_orientation_is_deterministic():
    X=make_data()
    b1=fit_directional_basis(X)
    b2=fit_directional_basis(X.copy())
    assert np.allclose(b1.direction,b2.direction)
    anchor=int(np.argmax(np.abs(b1.direction)))
    assert b1.direction[anchor] > 0


def test_stronger_tilt_reduces_ess_on_nonconstant_scores():
    X=make_data()
    b=fit_directional_basis(X)
    s=b.score(X)
    e=[ess_ratio(normalized_tilt_weights(s,lam)) for lam in [0,.5,1,1.5,2]]
    assert all(e[i+1] <= e[i] + 1e-12 for i in range(len(e)-1))
    assert e[-1] < e[0]


def test_radial_score_path():
    X=make_data()
    b=fit_radial_basis(X)
    s=radial_score(X,b)
    assert len(s)==len(X)
    assert np.max(np.abs(s)) <= 3.0 + 1e-12


def test_split_is_disjoint_and_complete():
    a,b,c=paired_split_indices(1000,123)
    assert len(a)==400 and len(b)==250 and len(c)==350
    assert len(set(a)&set(b))==0 and len(set(a)&set(c))==0 and len(set(b)&set(c))==0
    assert len(set(a)|set(b)|set(c))==1000


def test_target_sampling_reproducible():
    p=np.arange(1,351,dtype=float)
    i1,u1=sample_target_indices(350,p,500,77)
    i2,u2=sample_target_indices(350,p,500,77)
    assert np.array_equal(i1,i2)
    assert u1==u2 and 0 < u1 <= 1


def test_seed_derivation_stable_and_stream_specific():
    a=derive_seed(2026081602,2,4,3,1)
    b=derive_seed(2026081602,2,4,3,1)
    c=derive_seed(2026081602,2,4,3,2)
    assert a==b and a!=c
